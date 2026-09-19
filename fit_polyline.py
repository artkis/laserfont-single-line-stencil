"""Fit the original cubic centreline font to tangent circular biarcs.

This compatibility export is an approximation, not the Bezier master.
Its sampled error budget is in millimetres at 20 mm cap height.
"""
from pathlib import Path
import json, math, hashlib

ROOT=Path(__file__).resolve().parent
TOL=0.012  # reserve margin for the independent 0.02 mm check
def add(a,b): return (a[0]+b[0],a[1]+b[1])
def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def mul(a,s): return (a[0]*s,a[1]*s)
def dot(a,b): return a[0]*b[0]+a[1]*b[1]
def norm(a): return math.hypot(*a)
def unit(a): return mul(a,1/norm(a))
def mix(a,b): return mul(add(a,b),.5)
def bez(cp,t):
    u=1-t
    return tuple(u**3*cp[0][i]+3*u*u*t*cp[1][i]+3*u*t*t*cp[2][i]+t**3*cp[3][i] for i in range(2))
def split(cp):
    a,b,c=mix(cp[0],cp[1]),mix(cp[1],cp[2]),mix(cp[2],cp[3])
    d,e=mix(a,b),mix(b,c);f=mix(d,e)
    return [cp[0],a,d,f],[f,e,c,cp[3]]
def arc(a,b,t):
    w=sub(b,a);n=(-t[1],t[0]);den=2*dot(w,n)
    if norm(w)<1e-9: raise ValueError('Zero arc')
    if abs(den)<1e-10:
        if dot(w,t)<=0: raise ValueError('Reverse line')
        return {'p':a,'q':b,'bulge':0.}
    r=dot(w,w)/den;c=add(a,mul(n,r))
    aa=math.atan2(a[1]-c[1],a[0]-c[0]);bb=math.atan2(b[1]-c[1],b[0]-c[0])
    sweep=(bb-aa)%(2*math.pi) if r>0 else -((aa-bb)%(2*math.pi))
    if abs(sweep)>math.pi*1.5: raise ValueError('Long arc')
    return {'p':a,'q':b,'bulge':math.tan(sweep/4),'center':c,'radius':abs(r),'angle':aa,'sweep':sweep}
def reverse(a):
    d=dict(a);d['p'],d['q']=a['q'],a['p'];d['bulge']=-a['bulge']
    if a['bulge']:d['angle']=a['angle']+a['sweep'];d['sweep']=-a['sweep']
    return d
def arcpoint(a,t):
    if not a['bulge']:return add(a['p'],mul(sub(a['q'],a['p']),t))
    q=a['angle']+a['sweep']*t
    return add(a['center'],mul((math.cos(q),math.sin(q)),a['radius']))
def line_distance(p,a,b):
    w=sub(b,a);l=dot(w,w)
    return norm(sub(p,add(a,mul(w,max(0,min(1,dot(sub(p,a),w)/l)))))) if l else norm(sub(p,a))
def arc_distance(p,a):
    if not a['bulge']:return line_distance(p,a['p'],a['q'])
    v=sub(p,a['center']);ang=math.atan2(v[1],v[0]);sw=a['sweep']
    progress=(ang-a['angle'])%(2*math.pi) if sw>0 else (a['angle']-ang)%(2*math.pi)
    if progress<=abs(sw)+1e-10:return abs(norm(v)-a['radius'])
    return min(norm(sub(p,a['p'])),norm(sub(p,a['q'])))
def biarc(cp):
    p,q=cp[0],cp[3];t0=unit(sub(cp[1],p));t1=unit(sub(q,cp[2]));v=sub(q,p)
    aa=2*(1-dot(t0,t1));bb=2*dot(v,add(t0,t1));cc=-dot(v,v)
    if abs(aa)<1e-12:
        if bb<=1e-12:raise ValueError('Degenerate')
        d=-cc/bb
    else:d=(-bb+math.sqrt(bb*bb-4*aa*cc))/(2*aa)
    m=mul(add(add(p,q),mul(sub(t0,t1),d)),.5)
    return [arc(p,m,t0),reverse(arc(q,m,mul(t1,-1)))]
def fit(cp,depth=0):
    try:
        arcs=biarc(cp)
        # Closest distances in both directions; dense independent audit follows.
        samples=[bez(cp,i/160) for i in range(161)]
        e1=max(min(arc_distance(p,a) for a in arcs) for p in samples)
        e2=max(min(line_distance(arcpoint(a,i/40),p,q) for p,q in zip(samples,samples[1:])) for a in arcs for i in range(41))
        if max(e1,e2)<=TOL:return arcs,max(e1,e2)
    except ValueError:pass
    if depth>=14:raise RuntimeError('Biarc fit failed')
    l,r=split(cp);a,ea=fit(l,depth+1);b,eb=fit(r,depth+1)
    return a+b,max(ea,eb)
def merged(segments):
    out=[]
    for s in segments:
        if out:
            p=out[-1]
            if not p['bulge'] and not s['bulge']:
                v,w=sub(p['q'],p['p']),sub(s['q'],s['p'])
                if abs(v[0]*w[1]-v[1]*w[0])<1e-9 and dot(v,w)>0:
                    p['q']=s['q'];continue
            elif p['bulge'] and s['bulge'] and norm(sub(p['center'],s['center']))<1e-7 and abs(p['radius']-s['radius'])<1e-7 and p['sweep']*s['sweep']>0 and abs(p['sweep']+s['sweep'])<math.pi*1.5:
                p['q']=s['q'];p['sweep']+=s['sweep'];p['bulge']=math.tan(p['sweep']/4);continue
        out.append(dict(s))
    return out
def main():
    raw=(ROOT/'glyphs-v2.json').read_bytes();src=json.loads(raw);glyphs={};report={}
    for char,g in src['glyphs'].items():
        paths=[];errs=[];arc_count=0;line_count=0;minlen=1e9
        for path in g['paths']:
            ss=[]
            for s in path:
                if s['type']=='LINE':ss.append({'p':s['p'],'q':s['q'],'bulge':0.})
                else:
                    aa,e=fit([s['p'],s['c1'],s['c2'],s['q']]);ss.extend(aa);errs.append(e)
            ss=merged(ss)
            pts=[[s['p'][0],s['p'][1],s['bulge']] for s in ss]+[[*ss[-1]['q'],0.]]
            paths.append(pts)
            for s in ss:
                if s['bulge']:arc_count+=1;ln=abs(s['sweep'])*s['radius']
                else:line_count+=1;ln=norm(sub(s['q'],s['p']))
                minlen=min(minlen,ln)
        glyphs[char]={'advance_mm':g['advance_mm'],'paths_xyb':paths}
        report[char]={'paths':len(paths),'arcs':arc_count,'lines':line_count,'max_sampled_error_mm':max(errs,default=0),'min_segment_length_mm':minlen if paths else None}
    metadata={'name':'laserfont2','source_sha256':hashlib.sha256(raw).hexdigest(),'height_mm':20,'target_validation_tolerance_mm':.02,'fit_sample_budget_mm':TOL,'method':'Adaptive tangent biarc approximation of original cubic Bezier spans; exact LINE spans preserved','error_scope':'Sampled bidirectional deviation; independent dense readback validation required'}
    (ROOT/'glyphs-v2-polyline.json').write_text(json.dumps({'metadata':metadata,'glyphs':glyphs},indent=2))
    (ROOT/'polyline-fit-report.json').write_text(json.dumps({'metadata':metadata,'glyphs':report},indent=2))
    print(json.dumps({'glyphs':len(glyphs),'paths':sum(g['paths'] for g in report.values()),'arcs':sum(g['arcs'] for g in report.values()),'lines':sum(g['lines'] for g in report.values()),'max_sampled_error_mm':max(g['max_sampled_error_mm'] for g in report.values())}))
if __name__=='__main__':main()
