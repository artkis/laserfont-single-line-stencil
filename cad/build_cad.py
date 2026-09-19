# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
"""Build an original SHX display font and exact Bezier AutoLISP commands.

SHX is only a controlled display approximation. LASER2/LASEROUT2 emit exact
degree-3 SPLINE entities from the source controls, never the SHX vectors.
No installation or foreground AutoCAD operation is performed.
"""
from pathlib import Path
import json, math, hashlib

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'glyphs-v2.json'
CHORD_TOL = 0.004
GRID = 100

def lerp(p, q, t): return [p[i]*(1-t)+q[i]*t for i in range(2)]
def distance(p, q): return math.dist(p, q)
def segment_distance(p, a, b):
    d = [b[i]-a[i] for i in range(2)]
    den = sum(x*x for x in d)
    t = max(0., min(1., sum((p[i]-a[i])*d[i] for i in range(2))/den)) if den else 0
    return distance(p, lerp(a, b, t))

def bezier_controls(s):
    if s['type'] == 'LINE':
        return [s['p'], lerp(s['p'], s['q'], 1/3), lerp(s['p'], s['q'], 2/3), s['q']]
    return [s['p'], s['c1'], s['c2'], s['q']]

def split(c):
    a,b,d = [lerp(c[i], c[i+1], .5) for i in range(3)]
    e,f = lerp(a,b,.5),lerp(b,d,.5)
    g=lerp(e,f,.5)
    return [c[0],a,e,g],[g,f,d,c[3]]

def flatten(c, depth=0):
    if max(segment_distance(c[1],c[0],c[3]), segment_distance(c[2],c[0],c[3])) <= CHORD_TOL:
        return [c[0],c[3]]
    assert depth < 20
    a,b=split(c)
    return flatten(a,depth+1)[:-1]+flatten(b,depth+1)

def point(c,t):
    return [sum(c[k][i]*math.comb(3,k)*t**k*(1-t)**(3-k) for k in range(4)) for i in range(2)]

class Shape:
    def __init__(self):
        self.codes=[3,GRID,5];self.loc=[0.,0.];self.decoded=[]
    def move(self,p,draw=False):
        self.codes.append(1 if draw else 2)
        ds=[round((p[i]-self.loc[i])*GRID) for i in range(2)]
        n=max(1,math.ceil(max(map(abs,ds))/127));prev=[0,0]
        for k in range(1,n+1):
            nxt=[round(v*k/n) for v in ds];delta=[nxt[i]-prev[i] for i in range(2)]
            if any(delta):
                self.codes.extend([8,*delta]);q=[self.loc[i]+delta[i]/GRID for i in range(2)]
                if draw:self.decoded.append((self.loc[:],q[:]))
                self.loc=q
            prev=nxt
    def start(self,p):
        self.codes.extend([2,6,5]);self.loc=[0.,0.];self.move(p)
    def finish(self,advance):
        self.codes.extend([2,6]);self.loc=[0.,0.];self.move([advance,0.]);self.codes.extend([4,GRID,0])
        assert len(self.codes) <= 2000, len(self.codes)
        return self.codes

def record(cp,codes,name):
    lines=[f'*{cp:05X},{len(codes)},{name}'];line=''
    for i,v in enumerate(codes):
        token=str(v)+(',' if i+1<len(codes) else '')
        if len(line)+len(token)>100:lines.append(line);line=''
        line+=token
    if line:lines.append(line)
    return lines

def lisp(o):
    if isinstance(o,str):return json.dumps(o)
    if isinstance(o,(int,float)):return format(o,'.15g')
    return '('+' '.join(lisp(x) for x in o)+')'

def exact_path(path):
    if len(path)==1 and path[0]['type']=='LINE':return ['LINE',path[0]['p'],path[0]['q']]
    controls=[]
    for i,s in enumerate(path):
        c=bezier_controls(s)
        if i:assert distance(controls[-1],c[0])<1e-8
        controls+=c if not i else c[1:]
    n=len(path);knots=[0.]*4+[float(i) for i in range(1,n) for _ in range(3)]+[float(n)]*4
    assert len(knots)==len(controls)+4
    return ['SPLINE',controls,knots]

def main():
    raw=SOURCE.read_bytes();src=json.loads(raw);glyphs=src['glyphs'];proof={};codepoints={};exact=[]
    for ch,g in glyphs.items():
        shape=Shape();mapping=[]
        for path in g['paths']:
            assert path
            shape.start(path[0]['p'])
            for seg in path:
                start=len(shape.decoded)
                pts=[seg['p'],seg['q']] if seg['type']=='LINE' else flatten(bezier_controls(seg))
                for p in pts[1:]:shape.move(p,True)
                mapping.append((seg,start,len(shape.decoded)))
        codepoints[ch]=shape.finish(g['advance_mm'])
        error=0.
        for seg,start,end in mapping:
            c=bezier_controls(seg)
            error=max(error,max(min(segment_distance(point(c,k/256),a,b) for a,b in shape.decoded[start:end]) for k in range(257)))
        proof[ch]={'bytes':len(shape.codes),'sampled_display_error_mm':error,'display_segments':len(shape.decoded),'exact_paths':len(g['paths'])}
        assert error <= .012, (ch,error)
        exact.append([ch,g['advance_mm'],[exact_path(p) for p in g['paths']]])
    space=float(glyphs.get(' ',{}).get('advance_mm',src.get('metadata',{}).get('space_advance_mm',8.)))
    missing=Shape()
    for path in [[[0,0],[10,0],[10,20],[0,20],[0,0]],[[0,0],[10,20]],[[0,20],[10,0]]]:
        missing.start(path[0])
        for p in path[1:]:missing.move(p,True)
    fallback=missing.finish(14.)
    lines=['; SPDX-License-Identifier: OFL-1.1',
           '; Copyright (c) 2026 Artkis. Font data: SIL Open Font License 1.1; see OFL.txt.',
           '; laserfont2 display only. Exact Bezier cutting geometry: LASER2 / LASEROUT2.',
           '; SHX has no native Bezier primitive; this file is a controlled display approximation.',
           '*UNIFONT,6,laserfont2','20,0,0,0,0,0']+record(10,[2,8,0,-28,0],'linefeed')
    for cp in range(32,127):
        ch=chr(cp)
        if ch==' ':
            b=Shape();codes=b.finish(space)
        else:codes=codepoints.get(ch.upper(),fallback)
        lines+=record(cp,codes,'glyph_'+str(cp))
    (OUT/'laserfont2.shp').write_text('\n'.join(lines)+'\n',encoding='ascii')
    header=(';;; laserfont2 original minimal two-bridge Bezier geometry.\n'
            ';;; Copyright (c) 2026 Artkis.\n'
            ';;; Mixed-license file: embedded font designs/data are OFL-1.1 (OFL.txt);\n'
            ';;; the AutoLISP utility program is MIT (LICENSE-MIT.txt).\n'
            ';;; Never use the SHX display tessellation as a cutting path.\n'
            ';;; BEGIN FONT DATA -- SPDX-License-Identifier: OFL-1.1\n')
    data='(setq *lf2:glyphs* \''+lisp(exact)+')\n(setq *lf2:space* '+lisp(space)+')\n'
    poly_source=OUT.parent/'glyphs-v2-polyline.json'
    polydata=[]
    if poly_source.exists():
        poly_payload=json.loads(poly_source.read_text(encoding='utf-8'))
        assert poly_payload['metadata']['source_sha256']==hashlib.sha256(raw).hexdigest(), 'Arc-fit data was built from a different glyph revision'
        polys=poly_payload['glyphs']
        assert set(polys)==set(glyphs), 'Arc-fit glyph coverage differs from the original font'
        for ch,g in polys.items():
            assert abs(g['advance_mm']-glyphs[ch]['advance_mm'])<1e-9
            assert len(g['paths_xyb'])==len(glyphs[ch]['paths'])
            polydata.append([ch,g['advance_mm'],g['paths_xyb']])
    data+='(setq *lf2:poly-glyphs* \''+lisp(polydata)+')\n'
    program=header+data+';;; END FONT DATA\n\n'+(OUT/'runtime.lsp').read_text(encoding='utf-8')
    (OUT/'LASER2.lsp').write_text(program,encoding='ascii')
    (OUT/'compiled-glyphs-v2.json').write_bytes(raw)
    result={'source_sha256':hashlib.sha256(raw).hexdigest(),'source':'../glyphs-v2.json','cap_height':20,
            'shx_display_only':True,'display_chord_bound_mm':CHORD_TOL,'coordinate_grid_mm':1/GRID,
            'conservative_display_bound_mm':CHORD_TOL+math.sqrt(2)/GRID/2,
            'maximum_sampled_display_error_mm':max(x['sampled_display_error_mm'] for x in proof.values()),
            'exact_emission':'LINE or piecewise cubic nonrational clamped SPLINE; source controls preserved',
            'font_name':'laserfont2','font_license':'OFL-1.1','utility_license':'MIT','copyright':'Copyright (c) 2026 Artkis','glyphs':proof}
    (OUT/'cad-build-proof.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='glyphs'},indent=2))

if __name__=='__main__':main()
