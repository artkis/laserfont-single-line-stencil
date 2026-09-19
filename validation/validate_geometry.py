"""Validate laserfont2 geometry without importing the authoring or export code.

Run: python validation/validate_geometry.py --root .
Dependencies: ezdxf >= 1.4 and shapely >= 2.0.
Only geometry is tested; CAM routing, machine behavior and material strength
require separate process verification.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, math
from importlib.metadata import version
from pathlib import Path
import ezdxf
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import unary_union, polygonize, snap
CHORD=0.00025
TOL=CHORD

def dist(a,b):return math.dist(a,b)
def bez(cp,t):
    cp=[list(p) for p in cp]
    while len(cp)>1:cp=[[(1-t)*p[j]+t*q[j] for j in range(2)] for p,q in zip(cp,cp[1:])]
    return cp[0]
def cps(s):return [s['p'],s['c1'],s['c2'],s['q']]
def splithalf(cp):
    a=[cp];
    while len(a[-1])>1:a.append([[(p[j]+q[j])/2 for j in range(2)] for p,q in zip(a[-1],a[-1][1:])])
    return [x[0] for x in a],[x[-1] for x in reversed(a)]
def sample(s):
    if s['type']=='LINE':return [s['p'],s['q']]
    def rec(cp,depth=0):
        chord=LineString([cp[0],cp[3]])
        # Control hull bound catches overshoot and loops, including zero chord.
        err=max(chord.distance(Point(cp[i])) for i in (1,2))
        if err<=TOL or depth>=20:return [cp[0],cp[3]]
        a,b=splithalf(cp);return rec(a,depth+1)[:-1]+rec(b,depth+1)
    return rec(cps(s))
def bounds(s):
    pts=[s['p'],s['q']]
    if s['type']=='CUBIC':
        cp=cps(s)
        for k in range(2):
            p0,p1,p2,p3=[p[k] for p in cp]
            a=-p0+3*p1-3*p2+p3;b=2*(p0-2*p1+p2);c=p1-p0
            if abs(a)<1e-14:roots=[] if abs(b)<1e-14 else [-c/b]
            else:
                delta=b*b-4*a*c
                roots=[] if delta<0 else [(-b+math.sqrt(delta))/(2*a),(-b-math.sqrt(delta))/(2*a)]
            pts.extend(bez(cp,t) for t in roots if 0<t<1)
    return pts
def endpoint_derivative(s,end):
    if s['type']=='LINE':return [s['q'][i]-s['p'][i] for i in range(2)]
    a,b=(s['c2'],s['q']) if end else (s['p'],s['c1'])
    return [3*(b[i]-a[i]) for i in range(2)]
def tangent_angle(a,b):
    n=math.hypot(*a)*math.hypot(*b)
    if n<1e-12:return None
    return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/n))))
def curvature(s,t):
    if s['type']=='LINE':return 0.
    cp=cps(s);d=[3*(cp[i+1][k]-cp[i][k]) for k in range(2) for i in range(3)]
    d1=[(1-t)**2*d[k*3]+2*(1-t)*t*d[k*3+1]+t*t*d[k*3+2] for k in range(2)]
    d2=[6*((1-t)*(cp[2][k]-2*cp[1][k]+cp[0][k])+t*(cp[3][k]-2*cp[2][k]+cp[1][k])) for k in range(2)]
    denom=math.hypot(*d1)**3
    return None if denom<1e-15 else (d1[0]*d2[1]-d1[1]*d2[0])/denom

def audit_glyph(ch,g):
    faults=[];notes=[];lines=[];allpts=[];corners=[];jumps=[];segments=0
    if not math.isfinite(g['advance_mm']) or g['advance_mm']<=0:faults.append('invalid advance')
    for pi,path in enumerate(g['paths']):
        if not path:faults.append(f'empty path {pi}');continue
        poly=[]
        for si,s in enumerate(path):
            segments+=1
            if s['type'] not in ('LINE','CUBIC'):faults.append(f'bad type {pi}/{si}');continue
            pts=[s[k] for k in (('p','q') if s['type']=='LINE' else ('p','c1','c2','q'))]
            if not all(len(p)==2 and all(math.isfinite(v) for v in p) for p in pts):faults.append(f'nonfinite point {pi}/{si}')
            sp=sample(s);allpts.extend(bounds(s));poly.extend(sp if not poly else sp[1:])
            if LineString(sp).length<=1e-9:faults.append(f'zero segment {pi}/{si}')
            if si:
                prev=path[si-1]
                if dist(prev['q'],s['p'])>1e-8:faults.append(f'disconnected {pi}/{si}')
                angle=tangent_angle(endpoint_derivative(prev,True),endpoint_derivative(s,False))
                if angle is None:faults.append(f'zero derivative {pi}/{si}')
                elif angle>0.01:corners.append({'path':pi,'join':si,'angle_deg':round(angle,6)})
                ka,kb=curvature(prev,1),curvature(s,0)
                if ka is not None and kb is not None and abs(ka-kb)>1e-6:jumps.append({'path':pi,'join':si,'delta_per_mm':round(abs(ka-kb),6)})
        ln=LineString(poly);lines.append(ln)
        if ln.length<=1e-8:faults.append(f'zero path {pi}')
        if ln.is_ring or dist(path[0]['p'],path[-1]['q'])<=1e-8:faults.append(f'closed path {pi}')
        if not ln.is_simple:faults.append(f'self-intersecting path {pi}')
    height=max([p[1] for p in allpts],default=0)-min([p[1] for p in allpts],default=0)
    if ch not in '- ' and abs(height-20)>0.001:faults.append(f'height {height:.9f} !=20')
    intersections=[]
    for i,a in enumerate(lines):
        for j,b in enumerate(lines[i+1:],i+1):
            x=a.intersection(b)
            if not x.is_empty:
                cross=a.crosses(b);overlap=x.length
                contact='crossing' if cross else 'touch'
                if x.geom_type=='Point':
                    if min(x.distance(Point(p)) for line in (a,b) for p in (line.coords[0],line.coords[-1]))<1e-7:
                        cross=False;contact='endpoint_contact'
                    else:
                        # Shapely's crosses includes an interior tangential touch.
                        # Distinguish a local tangency from a transverse crossing.
                        dirs=[]
                        for line in (a,b):
                            t=line.project(x);p=line.interpolate(max(0,t-.01));q=line.interpolate(min(line.length,t+.01))
                            dirs.append((q.x-p.x,q.y-p.y))
                        angle=tangent_angle(*dirs)
                        if angle is not None and min(angle,180-angle)<1:
                            cross=False;contact='tangential_contact'
                intersections.append({'paths':[i,j],'type':x.geom_type,'contact':contact,'proper_crossing':cross,'overlap_mm':round(overlap,6),'wkt':x.wkt})
                if overlap>1e-7:faults.append(f'overlapping paths {i}/{j}')
                elif cross:faults.append(f'crossing paths {i}/{j}')
    cycles=list(polygonize(unary_union(lines))) if lines else []
    if cycles:faults.append(f'{len(cycles)} fully enclosed cut cycles / possible dropout islands')
    if g.get('bridge_count') != 2*g.get('counter_count',0):faults.append('metadata bridge count mismatch')
    gaps=[];gapchecks=[];allcuts=unary_union(lines) if lines else None
    bridge_records=g.get('bridges',[])
    if len(bridge_records)!=g.get('bridge_count',0):faults.append('bridge records/count mismatch')
    for ci in range(g.get('counter_count',0)):
        if sum(b['counter']==ci for b in bridge_records)!=2:faults.append(f'counter {ci} does not have two bridge records')
    for bi,b in enumerate(bridge_records):
        gap=LineString([b['p'],b['q']]);gaps.append(gap)
        actual=gap.length;deviation=abs(actual-b['centerline_gap_mm'])
        endpoints=[Point(p).distance(allcuts) for p in (b['p'],b['q'])]
        # Remove 1% at either end to ignore intended endpoint contacts with cut paths.
        a,c=b['p'],b['q'];interior=LineString([[a[k]*.99+c[k]*.01 for k in range(2)],[a[k]*.01+c[k]*.99 for k in range(2)]])
        cuts_inside=not interior.intersection(allcuts).is_empty
        if actual<2.99:faults.append(f'bridge {bi} narrower than 2.99 mm')
        if deviation>1e-6:faults.append(f'bridge {bi} width metadata mismatch')
        if max(endpoints)>TOL*1.1:faults.append(f'bridge {bi} endpoint not on cut: {max(endpoints):.6f}mm')
        if cuts_inside:faults.append(f'bridge {bi} crossed by a cut')
        gapchecks.append({'bridge':bi,'counter':b['counter'],'width_mm':actual,'endpoint_distance_from_cut_mm':endpoints,'interior_cut_intersection':cuts_inside})
    conceptual=[]
    if gaps:
        # Snap sampled curves to known bridge endpoints before polygonizing. This
        # verifies omitted gaps would close the expected counters, rather than
        # merely trusting a declaration of "two bridges".
        targets=MultiPoint([p for b in bridge_records for p in (b['p'],b['q'])])
        graph=unary_union([snap(line,targets,TOL*1.1) for line in lines]+gaps)
        conceptual=list(polygonize(graph))
        if len(conceptual)!=g.get('counter_count'):faults.append(f'closing declared gaps produces {len(conceptual)} counters instead of {g.get("counter_count")}')
    return {'faults':faults,'notes':notes,'height_mm':height,'cut_paths':len(lines),'segments':segments,
            'length_mm_approx':sum(x.length for x in lines),'intersections':intersections,'closed_cut_cycles':len(cycles),
            'tangent_discontinuities':corners,'curvature_discontinuities':jumps,'counter_count':g.get('counter_count'),
            'bridge_count':g.get('bridge_count'),'bridge_checks':gapchecks,'conceptual_counter_cycles':len(conceptual)}

def check_dxf(file,glyphs,rows):
    d=ezdxf.readfile(file);es=list(d.modelspace());faults=[]
    if d.units!=4:faults.append('not millimetre units')
    if d.audit().has_errors:faults.append('DXF audit errors')
    expected=[]
    for text,x,y in rows:
        offset=0
        for ch in text:
            for path in glyphs[ch]['paths']:expected.append((path,x+offset,y,ch))
            offset+=glyphs[ch]['advance_mm']
    if len(es)!=len(expected):faults.append(f'entity count {len(es)} != {len(expected)}')
    worst=0;samples=0
    for i,(e,(path,x,y,ch)) in enumerate(zip(es,expected)):
        if e.dxftype() not in ('LINE','SPLINE'):faults.append(f'forbidden entity {e.dxftype()}');continue
        if e.dxftype()=='LINE':
            if len(path)!=1 or path[0]['type']!='LINE':faults.append(f'LINE type mismatch {i}')
            else:
                for actual,p in zip((e.dxf.start,e.dxf.end),(path[0]['p'],path[0]['q'])):worst=max(worst,dist(actual,(x+p[0],y+p[1],0)))
        else:
            if e.dxf.degree!=3 or e.closed:faults.append(f'bad spline {i}')
            tool=e.construction_tool()
            for j,s in enumerate(path):
                for k in range(17):
                    t=k/16
                    p=bez(cps(s),t) if s['type']=='CUBIC' else [(1-t)*s['p'][a]+t*s['q'][a] for a in range(2)]
                    actual=tool.point(j+t);err=dist(actual,(x+p[0],y+p[1],0));samples+=1;worst=max(worst,err)
    if worst>1e-7:faults.append(f'DXF geometry error {worst}mm')
    return {'file':file.name,'faults':faults,'entities':len(es),'curve_samples':samples,'max_error_mm':worst,
            'text_entities':sum(e.dxftype() in ('TEXT','MTEXT') for e in es),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}

def arc_samples(v,w):
    p=v[:2];q=w[:2];b=v[2];length=math.dist(p,q)
    if abs(b)<1e-12:return [p,q],length,0
    if length<1e-12:raise ValueError('Zero length chord with arc bulge')
    center=[(p[0]+q[0])/2-(q[1]-p[1])*(1-b*b)/(4*b),
            (p[1]+q[1])/2+(q[0]-p[0])*(1-b*b)/(4*b)]
    radius=math.dist(center,p);theta=4*math.atan(b);a=math.atan2(p[1]-center[1],p[0]-center[0])
    step=2*math.acos(max(-1,min(1,1-CHORD/radius)))
    n=max(8,math.ceil(abs(theta)/max(step,1e-8)))
    points=[[center[0]+radius*math.cos(a+theta*i/n),center[1]+radius*math.sin(a+theta*i/n)] for i in range(n+1)]
    points[0]=p;points[-1]=q
    return points,abs(theta*radius),radius

def end_tangents(v,w):
    dx,dy=w[0]-v[0],w[1]-v[1];half=2*math.atan(v[2])
    c,s=math.cos(half),math.sin(half)
    return [(dx*c+dy*s,dy*c-dx*s),(dx*c-dy*s,dy*c+dx*s)]

def check_fit(source,polyfile):

    src=json.loads(source.read_text());poly=json.loads(polyfile.read_text());faults=[];rows={}
    sourcehash=hashlib.sha256(source.read_bytes()).hexdigest()
    if poly['metadata']['source_sha256']!=sourcehash:faults.append('source hash differs')
    for c,g in src['glyphs'].items():
        pp=poly['glyphs'][c]['paths_xyb'];gs=[];maxerr=0;mins=[];minr=[];arcs=0;straight=0;lns=[];tangent_jumps=[]
        if len(pp)!=len(g['paths']):faults.append(f'{c}: path count differs')
        for i,(path,vertices) in enumerate(zip(g['paths'],pp)):
            points=[];cp=[]
            for s in path:
                x=sample(s);points.extend(x if not points else x[1:])
            for v,w in zip(vertices,vertices[1:]):
                if len(v)!=3 or not all(math.isfinite(a) for a in v):faults.append(f'{c}/{i}: invalid vertex')
                x,length,r=arc_samples(v,w);cp.extend(x if not cp else x[1:]);mins.append(length)
                if r:arcs+=1;minr.append(r)
                else:straight+=1
            for j in range(1,len(vertices)-1):
                angle=tangent_angle(end_tangents(vertices[j-1],vertices[j])[1],end_tangents(vertices[j],vertices[j+1])[0])
                if angle is None:faults.append(f'{c}/{i}: zero tangent at {j}')
                elif angle>.01:tangent_jumps.append({'path':i,'vertex':j,'angle_degrees':angle})
            original=LineString(points);fitted=LineString(cp);lns.append(fitted)
            if fitted.length<=1e-10 or fitted.is_ring or not fitted.is_simple:faults.append(f'{c}/{i}: zero/closed/self-crossing path')
            start=math.dist(path[0]['p'],vertices[0][:2]);end=math.dist(path[-1]['q'],vertices[-1][:2])
            if max(start,end)>1e-7:faults.append(f'{c}/{i}: endpoint changed')
            if abs(vertices[-1][2])>1e-12:faults.append(f'{c}/{i}: terminal bulge should be zero')
            # Dense checks in both directions, computed without importing fitter.
            a=max(Point(p).distance(fitted) for p in points)
            b=max(Point(p).distance(original) for p in cp)
            err=max(a,b);maxerr=max(maxerr,err)
            if err+2*CHORD>.02:faults.append(f'{c}/{i}: deviation plus sampling allowance exceeds .02mm: {err+2*CHORD}')
            gs.append({'path':i,'source_samples':len(points),'arc_samples':len(cp),'source_to_fit_mm':a,'fit_to_source_mm':b,'endpoint_error_mm':max(start,end)})
        cycles=list(polygonize(unary_union(lns))) if lns else []
        if cycles:faults.append(f'{c}: fitted curves have closed cut cycles')
        contacts=[]
        for i,a in enumerate(lns):
            for j,b in enumerate(lns[i+1:],i+1):
                intersect=a.intersection(b)
                if not intersect.is_empty:
                    contacts.append({'paths':[i,j],'type':intersect.geom_type,'overlap_mm':intersect.length})
                    if intersect.length>1e-5:faults.append(f'{c}: new overlap {i}/{j}')
        bridges=[];allcuts=unary_union(lns) if lns else None
        for i,b in enumerate(g.get('bridges',[])):
            p,q=b['p'],b['q'];ep=max(Point(x).distance(allcuts) for x in (p,q))
            inside=LineString([[p[k]*.99+q[k]*.01 for k in range(2)],[p[k]*.01+q[k]*.99 for k in range(2)]])
            crossed=not inside.intersection(allcuts).is_empty
            if ep>2*CHORD:faults.append(f'{c}: bridge {i} endpoint changed beyond sampling bound {ep}')
            if crossed:faults.append(f'{c}: fitted cut intersects bridge {i}')
            bridges.append({'bridge':i,'endpoint_error_mm':ep,'crossed_by_cut':crossed})
        if tangent_jumps:faults.append(f'{c}: {len(tangent_jumps)} tangent discontinuities >0.01deg')
        rows[c]={'paths':len(pp),'arcs':arcs,'lines':straight,'max_dense_deviation_mm':maxerr,'min_segment_length_mm':min(mins,default=0),
                 'min_arc_radius_mm':min(minr,default=0),'checks':gs,'closed_cut_cycles':len(cycles),'tangent_jumps':tangent_jumps,
                 'bridge_checks':bridges,'contacts':contacts,'segments_below_0.25mm':sum(v<.25 for v in mins),
                 'segments_below_0.5mm':sum(v<.5 for v in mins),'segments_below_1mm':sum(v<1 for v in mins)}
    result={'source_sha256':sourcehash,'polyline_sha256':hashlib.sha256(polyfile.read_bytes()).hexdigest(),
            'method':'Independent bulge-to-circle reconstruction; adaptive Bezier and circular arc sampling with 0.00025mm chord-distance bounds; dense bidirectional nearest-distance checks.',
            'limits':'Geometric validation only. Arc fitting is an approximation of the exact Bezier master; no CypCut or machine acceptance implied.',
            'sampling_allowance_mm':2*CHORD,'max_deviation_mm':max(x['max_dense_deviation_mm'] for x in rows.values()),
            'faults':faults,'glyphs':rows}
    return result


def check_poly_dxf(file,glyphs,rows):
    d=ezdxf.readfile(file);es=list(d.modelspace());faults=[];expected=[]
    if d.units!=4:faults.append('not millimetre units')
    if d.audit().has_errors:faults.append('DXF audit errors')
    for text,x,y in rows:
        off=0
        for ch in text:
            for path in glyphs[ch]['paths_xyb']:expected.append((path,x+off,y))
            off+=glyphs[ch]['advance_mm']
    if len(es)!=len(expected):faults.append('wrong entity count')
    maxxy=0.;maxb=0.;arcs=0;lines=0
    for i,(e,(path,x,y)) in enumerate(zip(es,expected)):
        if e.dxftype()!='LWPOLYLINE':faults.append(f'wrong entity type {i}');continue
        if e.closed:faults.append(f'closed polyline {i}')
        if e.dxf.get('const_width',0)!=0:faults.append(f'nonzero width {i}')
        if e.dxf.get('elevation',0)!=0:faults.append(f'nonzero elevation {i}')
        points=list(e.get_points('xyseb'))
        if len(points)!=len(path):faults.append(f'wrong vertex count {i}')
        for (px,py,s,t,b),(sx,sy,sb) in zip(points,path):
            maxxy=max(maxxy,math.dist((px,py),(x+sx,y+sy)));maxb=max(maxb,abs(b-sb))
            if s or t:faults.append(f'nonzero per-vertex width {i}')
        arcs+=int(sum(abs(p[4])>1e-12 for p in points[:-1]));lines+=int(sum(abs(p[4])<=1e-12 for p in points[:-1]))
    if maxxy>1e-8 or maxb>1e-12:faults.append('polyline readback mismatch')
    return {'file':file.name,'faults':faults,'entities':len(es),'arcs':arcs,'lines':lines,
        'max_vertex_error_mm':maxxy,'max_bulge_error':maxb,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    ap.add_argument('--report',type=Path,default=None)
    args=ap.parse_args();root=args.root.resolve()
    source=root/'glyphs-v2.json';polyfile=root/'glyphs-v2-polyline.json'
    src=json.loads(source.read_text(encoding='utf-8'));poly=json.loads(polyfile.read_text(encoding='utf-8'));glyphs=src['glyphs']
    report={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_file':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'dependencies':{'ezdxf':version('ezdxf'),'shapely':version('shapely')},
        'sampling_tolerance_mm':TOL,'glyphs':{c:audit_glyph(c,g)for c,g in glyphs.items()},'dxf':[],
        'limits':'Geometric checks only. Curves/topology are sampled with stated tolerances. No CAM interpretation, toolpath sequencing, timing, kerf, thermal behavior, machine motion or material-strength acceptance is implied.'}
    expected=set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ')
    report['font_set_faults']=[] if set(glyphs)==expected else ['Expected A-Z, 0-9, hyphen and space']
    report['arc_fit']=check_fit(source,polyfile)
    rows=[(t,0,-35*i)for i,t in enumerate(['ABCDEFGHIJKLM','NOPQRSTUVWXYZ','0123456789-','PANEL-A01','LASER-02','B8-S5-J1-O0'])]
    for prefix,layout in [('laserfont2-alphabet',rows),('PANEL-A01-H20',[('PANEL-A01',0,0)])]:
        for mode in ('bezier','polyline'):
            f=root/'examples'/f'{prefix}-{mode}.dxf'
            if not f.exists():report['dxf'].append({'file':f.name,'faults':['missing example file']})
            elif mode=='bezier':report['dxf'].append(check_dxf(f,glyphs,layout))
            else:report['dxf'].append(check_poly_dxf(f,poly['glyphs'],layout))
    count=len(report['font_set_faults'])+sum(len(x['faults'])for x in report['glyphs'].values())+len(report['arc_fit']['faults'])+sum(len(x['faults'])for x in report['dxf'])
    report['fault_count']=count;report['status']='PASS' if count==0 else 'FAIL'
    dest=args.report or Path(__file__).resolve().parent/'geometry-report.json'
    dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'fault_count':count,'source_sha256':report['source_sha256'],
        'max_arc_fit_deviation_mm':report['arc_fit']['max_deviation_mm'],'dxf':report['dxf']},indent=2))
    raise SystemExit(0 if count==0 else 1)

if __name__=='__main__':main()
