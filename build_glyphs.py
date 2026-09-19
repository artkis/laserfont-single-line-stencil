"""Original laserfont2 drawing skeletons. No installed/font-program glyphs reused.

Copyright (c) 2026 Artkis. Font design source licensed under the
SIL Open Font License 1.1 (OFL-1.1). No Reserved Font Names.
See OFL.txt or https://openfontlicense.org for the full license.

20 mm uppercase, cubic Bezier centerlines, two deliberate gaps per counter.
Construction control polygons are not cutting polylines. Do not flatten these
curves into many short machine moves. Machine interpolation remains untested.
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
G = {}

def line(p,q): return dict(type='LINE',p=list(p),q=list(q))
def cubic(p,a,b,q): return dict(type='CUBIC',p=list(p),c1=list(a),c2=list(b),q=list(q))
def rev(path):
    return [line(s['q'],s['p']) if s['type']=='LINE' else cubic(s['q'],s['c2'],s['c1'],s['p']) for s in path[::-1]]
def xf(path, fn): return [{k:fn(v) if k in ('p','q','c1','c2') else v for k,v in s.items()} for s in path]
def flip(path): return xf(path,lambda p:[p[0],20-p[1]])
def point(s,t):
    if s['type']=='LINE': return [(1-t)*s['p'][i]+t*s['q'][i] for i in (0,1)]
    return [(1-t)**3*s['p'][i]+3*(1-t)**2*t*s['c1'][i]+3*(1-t)*t*t*s['c2'][i]+t**3*s['q'][i] for i in (0,1)]
def lerp(a,b,t): return [x+(y-x)*t for x,y in zip(a,b)]
def split(s,t):
    if s['type']=='LINE':
        m=point(s,t);return line(s['p'],m),line(m,s['q'])
    a=lerp(s['p'],s['c1'],t);b=lerp(s['c1'],s['c2'],t);c=lerp(s['c2'],s['q'],t)
    d=lerp(a,b,t);e=lerp(b,c,t);m=lerp(d,e,t)
    return cubic(s['p'],a,d,m),cubic(m,e,c,s['q'])
def gap_segment(s,t=.5,gap=3):
    lo,hi=0,min(t,1-t)
    for _ in range(60):
        h=(lo+hi)/2
        if math.dist(point(s,t-h),point(s,t+h))<gap:lo=h
        else:hi=h
    h=hi
    first,_=split(s,t-h);_,last=split(s,t+h)
    return first,last,(first['q'],last['p'])
def rounded(points,r=1.5):
    """Tangent quadratic corner fillets represented as exact cubics."""
    out=[];cur=points[0]
    for i,b in enumerate(points[1:-1],1):
        a,c=points[i-1],points[i+1]
        d=min(r,math.dist(a,b)*.42,math.dist(b,c)*.42)
        p=lerp(b,a,d/math.dist(a,b));q=lerp(b,c,d/math.dist(b,c))
        if math.dist(cur,p)>1e-9:out.append(line(cur,p))
        out.append(cubic(p,lerp(p,b,2/3),lerp(q,b,2/3),q));cur=q
    if math.dist(cur,points[-1])>1e-9:out.append(line(cur,points[-1]))
    return out
def bridge(p,q,counter):return dict(counter=counter,p=list(p),q=list(q),centerline_gap_mm=math.dist(p,q))
def add(char,paths,counters=0,bridges=(),note=''):
    samples=[point(s,t/200) for path in paths for s in path for t in range(201)]
    if samples:
        xmin=min(p[0] for p in samples);xmax=max(p[0] for p in samples)
        ymin=min(p[1] for p in samples);ymax=max(p[1] for p in samples)
        scale=20/(ymax-ymin) if char not in '- ' else 1
        fn=lambda p:[(p[0]-xmin)*scale,(p[1]-ymin)*scale if char not in '- ' else p[1]]
        paths=[xf(path,fn) for path in paths]
        bridges=[bridge(fn(b['p']),fn(b['q']),b['counter']) for b in bridges]
        width=(xmax-xmin)*scale
    else:width=4
    G[char]=dict(width_mm=width,advance_mm=width+4,paths=paths,counter_count=counters,
                 bridge_count=len(bridges),bridges=bridges,path_count=len(paths),design_note=note)

# Open, legible skeletons. Smooth joins are tangent, not universally curvature-continuous.
add('C',[[cubic((12,18),(10,19.5),(8.5,20),(6,20)),
          cubic((6,20),(2,20),(0,17),(0,13)),line((0,13),(0,7)),
          cubic((0,7),(0,3),(2,0),(6,0)),cubic((6,0),(8.5,0),(10,0.5),(12,2))]])
add('E',[rounded([(12,20),(0,20),(0,0),(12,0)],2),[line((0,10),(9,10))]])
add('F',[rounded([(0,0),(0,20),(12,20)],2),[line((0,11),(9,11))]])
add('G',[[cubic((12,18),(10,19.5),(8.5,20),(6,20)),cubic((6,20),(2,20),(0,17),(0,13)),
          line((0,13),(0,7)),cubic((0,7),(0,3),(2,0),(6,0)),
          cubic((6,0),(10,0),(12,2),(12,6)),line((12,6),(12,8)),
          cubic((12,8),(12,9.33),(11.33,10),(10,10)),line((10,10),(7,10))]])
add('H',[[line((0,0),(0,20))],[line((12,0),(12,20))],[line((0,10),(12,10))]])
add('I',[[line((0,20),(8,20))],[line((4,20),(4,0))],[line((0,0),(8,0))]],note='Top and bottom bars distinguish I from numeral 1.')
add('J',[[line((11,20),(11,6)),
    cubic((11,6),(11,2),(9,0),(5.5,0)),cubic((5.5,0),(2,0),(0,2),(0,5))]],note='Conventional hook; one path.')
add('K',[[line((0,0),(0,20))],[cubic((12,20),(6,15),(0,14),(0,10)),
          cubic((0,10),(0,6),(6,5),(12,0))]],note='Two paths, curved diagonal waist touches upright tangentially.')
add('L',[rounded([(0,20),(0,0),(12,0)],2)])
add('M',[rounded([(0,0),(0,20),(7,10),(14,20),(14,0)],1.2)])
add('N',[rounded([(0,0),(0,20),(13,0),(13,20)],1.4)])
add('S',[[cubic((12,18),(10.5,19.5),(8.5,20),(6,20)),cubic((6,20),(2.4,20),(0,18.2),(0,15.2)),
          cubic((0,15.2),(0,12.2),(3.5,11),(6,10)),
          cubic((6,10),(8.5,9),(12,7.8),(12,4.8)),
          cubic((12,4.8),(12,1.8),(9.6,0),(6,0)),cubic((6,0),(3.5,0),(1.5,.5),(0,2))]])
add('T',[[line((0,20),(14,20))],[line((7,20),(7,0))]])
add('U',[[line((0,20),(0,6)),cubic((0,6),(0,2),(2,0),(6,0)),
          cubic((6,0),(10,0),(12,2),(12,6)),line((12,6),(12,20))]])
add('V',[rounded([(0,20),(6,0),(12,20)],2)])
add('W',[rounded([(0,20),(3,0),(8,10),(13,0),(16,20)],1.6)])
xa,xb,xgap=gap_segment(line((0,0),(12,20)))
add('X',[[line((0,20),(12,0))],[xa],[xb]],note='Three paths avoid recutting the central intersection; one diagonal has a 3 mm center gap, not an enclosed counter.')
yupper=rounded([(0,20),(6,11),(12,20)],1.4)
yp=point(next(s for s in yupper if s['type']=='CUBIC'),.5)
add('Y',[yupper,[line(yp,(6,0))]])
add('Z',[rounded([(0,20),(12,20),(0,0),(12,0)],1.4)])

# A: lower continuous crossbar/feet and separate upper arch, two diagonal gaps.
lower=rounded([(0,0),(3,8),(11,8),(14,0)],1.2)
upper=[line((4.2,11.2),(5.5,16.8)),cubic((5.5,16.8),(6.02,19.04),(6.2,20),(7,20)),
       cubic((7,20),(7.8,20),(7.98,19.04),(8.5,16.8)),line((8.5,16.8),(9.8,11.2))]
# The continuous lower path endpoints adjacent to the gaps are on the rounded shoulders.
# Add no invisible cutter segments across the deliberately separated crown.
shoulders=[point(s,.5) for s in lower if s['type']=='CUBIC']
add('A',[lower,upper],1,[bridge(shoulders[0],(4.2,11.2),0),bridge(shoulders[1],(9.8,11.2),0)],
    'Two counter bridges; crown is separated from a rounded feet/crossbar path.')

# Ellipse Beziers split at left/right equator: two explicit 3 mm bridges.
def oval(width=12,height=20,cy=10):
    rx=width/2;ry=height/2;a=math.asin(1.5/ry)
    def arc(t0,t1):
        n=math.ceil(abs(t1-t0)/(math.pi/2));out=[]
        for i in range(n):
            u=t0+(t1-t0)*i/n;v=t0+(t1-t0)*(i+1)/n;k=4/3*math.tan((v-u)/4)
            p=[rx+rx*math.cos(u),cy+ry*math.sin(u)];q=[rx+rx*math.cos(v),cy+ry*math.sin(v)]
            out.append(cubic(p,[p[0]-k*rx*math.sin(u),p[1]+k*ry*math.cos(u)],
                             [q[0]+k*rx*math.sin(v),q[1]-k*ry*math.cos(v)],q))
        return out
    top=arc(a,math.pi-a);bottom=arc(math.pi+a,2*math.pi-a)
    gaps=[bridge(top[-1]['q'],bottom[0]['p'],0),bridge(bottom[-1]['q'],top[0]['p'],0)]
    return [top,bottom],gaps
paths,gaps=oval();add('O',paths,1,gaps)
paths,gaps=oval(10);add('0',paths+[[line((3,5),(7,15))]],1,gaps,note='Narrow oval and isolated interior slash distinguish zero from O.')
paths,gaps=oval();qp=point(paths[1][-1],.55)
add('Q',paths+[[line(qp,(14,0))]],1,gaps,note='External Q tail begins exactly on bowl, not across it; no recut intersection.')

# D: opposite bridges on upright and right side, two continuous bowl halves.
dtop=[line((0,11.5),(0,18)),cubic((0,18),(0,19.33),(.67,20),(2,20)),line((2,20),(5,20)),
      cubic((5,20),(10,20),(13,17),(13,11.5))]
dbottom=flip(dtop)
add('D',[dtop,dbottom],1,[bridge((0,11.5),(0,8.5),0),bridge((13,11.5),(13,8.5),0)])

# P/R: first counter gap in top-right curve; second between return and stem.
pc=cubic((6,20),(10,20),(12,18),(12,15))
pa,pb,pg=gap_segment(pc,.57)
pstem=rounded([(0,0),(0,20),(6,20)],1.5)+[pa]
plobe=[pb,cubic((12,15),(12,12),(10,10),(6,10)),line((6,10),(3,10))]
pgaps=[bridge(*pg,0),bridge((3,10),(0,10),0)]
add('P',[pstem,plobe],1,pgaps)
add('R',[pstem,plobe,[line((0,10),(12,0))]],1,pgaps,
    'Diagonal leg distinguishes R; three cut paths, two counter gaps.')

# B: straight spine and ONE shared middle bar; two gaps for each bowl.
# Two inner bridge gaps converge on the bar end, each with a 3 mm chord.
# This removes the earlier parallel waist stubs and reduces five paths to four.
bc=cubic((6,20),(10,20),(12,18.5),(12,15))
ba,bb,bg=gap_segment(bc,.57)
bcap=[line((2,20),(6,20)),ba]
breturn=cubic((12,15),(12,12),(10,10),(6,10))
blo,bhi=0,1
for _ in range(60):
    bt=(blo+bhi)/2
    if math.dist(point(breturn,bt),(6,10))>3: blo=bt
    else: bhi=bt
bshort,_=split(breturn,blo)
bmiddle=[bb,bshort]
bspine=rev(bcap)+[cubic((2,20),(.667,20),(0,19.333),(0,18)),line((0,18),(0,2)),
                     cubic((0,2),(0,.667),(.667,0),(2,0))]+flip(bcap)
add('B',[bspine,bmiddle,flip(bmiddle),[line((0,10),(6,10))]],2,
    [bridge(*bg,0),bridge(bshort['q'],(6,10),0),
     bridge([bg[0][0],20-bg[0][1]],[bg[1][0],20-bg[1][1]],1),
     bridge([bshort['q'][0],20-bshort['q'][1]],(6,10),1)],
    'Four paths and one shared waist bar. Two independent 3 mm bridge gaps per bowl; inner gaps meet the bar endpoint from opposite sides.')

# Numerals: 1 includes angled head and base; 5 has clear straight top/left stem.
add('1',[rounded([(1,16),(5,20),(5,0)],1),[line((0,0),(10,0))]])
add('2',[[cubic((0,16),(0,18.5),(2.5,20),(6,20)),cubic((6,20),(9.5,20),(12,18.5),(12,15.5)),
          cubic((12,15.5),(12,11),(3,6),(1,2)),
          cubic((1,2),(.4,.8),(.6,0),(2,0)),line((2,0),(12,0))]])
add('3',[[cubic((0,18),(1.5,19.5),(3.5,20),(6,20)),cubic((6,20),(9.5,20),(12,18),(12,15.5)),
          cubic((12,15.5),(12,12.7),(5,12.8),(5,10)),
          cubic((5,10),(5,7.2),(12,7.3),(12,4.5)),
          cubic((12,4.5),(12,2),(9.5,0),(6,0)),cubic((6,0),(3.5,0),(1.5,.5),(0,2))]])
add('4',[rounded([(6,20),(0,8),(7,8)],1.1),[line((10,20),(10,0))]],1,
    [bridge((6,20),(10,20),0),bridge((7,8),(10,8),0)],'Open top and interrupted crossbar provide two counter openings.')
add('5',[rounded([(12,20),(0,20),(0,11),(6,11)],1.6)+[
    cubic((6,11),(10,11),(12,9),(12,5.5)),cubic((12,5.5),(12,2),(9.5,0),(6,0)),
    cubic((6,0),(3.5,0),(1.5,.5),(0,1.8))]])

# 6: hook flows continuously into left/bottom bowl; return ends before spine.
sixbase=[cubic((11,19),(9.5,20),(8,20),(6,20)),cubic((6,20),(2,20),(0,16),(0,11)),
         line((0,11),(0,6)),cubic((0,6),(0,2),(2,0),(6,0))]
sc=cubic((6,0),(10,0),(12,2),(12,6))
sa,sb,sg=gap_segment(sc,.57)
six1=sixbase+[sa]
six2=[sb,cubic((12,6),(12,9.5),(9.5,12),(6,12)),cubic((6,12),(4.5,12),(3.5,11.5),(3,11))]
sixgaps=[bridge(*sg,0),bridge((3,11),(0,11),0)]
add('6',[six1,six2],1,sixgaps)
fn=lambda p:[12-p[0],20-p[1]]
add('9',[xf(six1,fn),xf(six2,fn)],1,[bridge(fn(b['p']),fn(b['q']),0) for b in sixgaps])
add('7',[rounded([(0,20),(12,20),(2,0)],1.5)])

# 8: asymmetric lobes and diagonal waist, following the designer's hand sketch.
# One smaller top cap and two lower-bowl strokes give three paths in total.
eightpaths=[
 [cubic((3.1,11.3),(2,12.3),(1.5,14),(2,15.5)),
  cubic((2,15.5),(2.5,17),(3.5,20),(6,20)),
  cubic((6,20),(10,20),(12,16),(10.5,13.7))],
 [cubic((8.5,11.2),(7.3,10.37),(5.8,9.33),(4.6,8.5)),
  cubic((4.6,8.5),(2.8,7.255),(0,6.7),(0,4.5)),
  cubic((0,4.5),(0,3.3),(.5,2.1),(1.2,1.5))],
 [cubic((4.2,.3),(4.8,0),(5.4,0),(6,0)),
  cubic((6,0),(10,0),(12,2),(12,5)),
  cubic((12,5),(12,6.5),(10,7.5),(8.5,8.2))]
]
eightgaps=[bridge((3.1,11.3),(4.6,8.5),0),bridge((10.5,13.7),(8.5,11.2),0),
           bridge((1.2,1.5),(4.2,.3),1),bridge((8.5,11.2),(8.5,8.2),1)]
add('8',eightpaths,2,eightgaps,
    'Three paths form a smaller upper cap, larger lower bowl and diagonal waist. Two clear bridge gaps per counter, each at least 3 mm.')
add('-',[[line((0,10),(8,10))]])
G[' ']=dict(width_mm=4,advance_mm=8,paths=[],counter_count=0,bridge_count=0,bridges=[],path_count=0,design_note='Space')

def derivative(s,end=False):
    if s['type']=='LINE':return [s['q'][i]-s['p'][i] for i in (0,1)]
    return [3*(s['q'][i]-s['c2'][i]) if end else 3*(s['c1'][i]-s['p'][i]) for i in (0,1)]
for char,g in G.items():
    length=0;maxangle=0
    for path in g['paths']:
        for s in path:
            pts=[point(s,t/100) for t in range(101)]
            length+=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        for a,b in zip(path,path[1:]):
            assert math.dist(a['q'],b['p'])<1e-8,(char,a,b)
            v,w=derivative(a,True),derivative(b)
            norm=math.hypot(*v)*math.hypot(*w)
            if norm:maxangle=max(maxangle,math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(v,w))/norm)))))
        assert math.dist(path[0]['p'],path[-1]['q'])>1e-8
    g['cut_length_mm_approx']=length;g['max_internal_tangent_jump_deg']=maxangle
    assert g['bridge_count']==2*g['counter_count'],char
    assert all(b['centerline_gap_mm']>=3-1e-6 for b in g['bridges']),char

assert set(G)==set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ')
data=dict(metadata=dict(name='laserfont2',version='2.0.0',height_mm=20,bridges_per_counter=2,
    copyright='Copyright (c) 2026 Artkis',license='SIL Open Font License 1.1',spdx_license='OFL-1.1',reserved_font_names=[],
    bridge_gap_mm=3,geometry='single-line cubic Bezier centerlines',status='Geometry verified; CAM and machine qualification pending',
    intent='Reduce disconnected cutting paths and pierces, retain legibility, then soften turns.',
    curves='Cubic Beziers; tangent G1 joins where joined; not universal G2 curvature continuity.',
    exceptions='Intentional T or tangential junctions remain in several glyphs; X central crossover is interrupted. No duplicate strokes or intended closed cut loops.'),
    glyphs={ch:G[ch] for ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- '})
(HERE/'glyphs-v2.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps({ch:dict(paths=g['path_count'],length=round(g['cut_length_mm_approx'],2),bridges=g['bridge_count'],max_turn=round(g['max_internal_tangent_jump_deg'],2)) for ch,g in data['glyphs'].items()},indent=2))
