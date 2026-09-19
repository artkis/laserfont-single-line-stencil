"""Create permanent single-line LaserFont geometry; no font dependency in DXF.

Font designs/data: SIL OFL 1.1. Utility code: MIT. See LICENSING.md.
"""
from pathlib import Path
import argparse,json,math
import ezdxf
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'glyphs-v2.json'
EXAMPLES=ROOT/'examples'
def font(size):
    for name in ['DejaVuSans.ttf','Arial.ttf','LiberationSans-Regular.ttf']:
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default(size=size)
def paint_glyph(draw,g,x,y,scale=6,color='#84F0BE',width=3):
    for path in g['paths']:
        pts=sample_path(path)
        if len(pts)>1:draw.line([(x+a*scale,y-b*scale) for a,b in pts],fill=color,width=width,joint='curve')
def point(s, t):
    if s['type'] == 'LINE':
        return tuple((1-t)*a+t*b for a,b in zip(s['p'],s['q']))
    u=1-t
    return tuple(u**3*s['p'][i]+3*u*u*t*s['c1'][i]+3*u*t*t*s['c2'][i]+t**3*s['q'][i] for i in range(2))

def cubic(s):
    if s['type']=='CUBIC': return [s['p'],s['c1'],s['c2'],s['q']]
    p,q=s['p'],s['q']
    return [p,[(2*p[i]+q[i])/3 for i in range(2)],[(p[i]+2*q[i])/3 for i in range(2)],q]

def transform(p, x, y, scale=1, rotation=0):
    a=math.radians(rotation);c,s=math.cos(a),math.sin(a)
    return (x+scale*(p[0]*c-p[1]*s), y+scale*(p[0]*s+p[1]*c), 0)

def spline_data(path):
    cp=list(cubic(path[0]))
    for previous,s in zip(path,path[1:]):
        if math.dist(previous['q'],s['p'])>1e-7: raise ValueError('Disconnected stroke in source')
        cp.extend(cubic(s)[1:])
    count=len(path)
    knots=[0.0]*4+[float(i) for i in range(1,count) for _ in range(3)]+[float(count)]*4
    return cp,knots

def add_text(msp, glyphs, text, x=0, y=0, height=20, rotation=0, layer='ID_CUT_SINGLELINE'):
    if height<=0: raise ValueError('Height must be positive')
    unsupported=sorted(set(text.upper())-set(glyphs))
    if unsupported: raise ValueError('Unsupported characters: '+repr(unsupported))
    offset=0.;entities=[];scale=height/20
    for char in text.upper():
        g=glyphs[char]
        for path in g['paths']:
            def trans(p):return transform((p[0]+offset,p[1]),x,y,scale,rotation)
            if len(path)==1 and path[0]['type']=='LINE':
                e=msp.add_line(trans(path[0]['p']),trans(path[0]['q']),dxfattribs={'layer':layer})
            else:
                cp,knots=spline_data(path)
                e=msp.add_open_spline([trans(p) for p in cp],degree=3,knots=knots,dxfattribs={'layer':layer})
            entities.append(e)
        offset+=g['advance_mm']
    return entities

def new_drawing():
    d=ezdxf.new('R2010');d.units=4;d.header['$MEASUREMENT']=1
    d.layers.new('ID_CUT_SINGLELINE',dxfattribs={'color':3,'lineweight':0})
    return d

def sample_path(path,n=90):
    out=[]
    for s in path:
        pts=[point(s,i/n) for i in range(n+1)] if s['type']=='CUBIC' else [s['p'],s['q']]
        out.extend(pts if not out else pts[1:])
    return out

def preview(glyphs):
    chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    img=Image.new('RGB',(1800,1080),'#17232B');d=ImageDraw.Draw(img)
    d.text((45,28),'laserfont2  /  20 mm  /  two bridges per counter',font=font(36),fill='#F0F4F7')
    d.text((45,78),'Original single-line Bezier paths. B and 8: two bridges in each lobe.',font=font(23),fill='#A6B5C0')
    for i,c in enumerate(chars):
        row,col=divmod(i,10);x=42+col*173;y=140+row*224
        d.rounded_rectangle((x,y,x+156,y+207),radius=8,outline='#32444E',width=1)
        g=glyphs[c];paint_glyph(d,g,x+(156-g['width_mm']*6)/2,y+151,6)
        d.text((x+12,y+176),c,font=font(21),fill='#F0F4F7')
        d.text((x+46,y+179),str(len(g['paths']))+' paths',font=font(16),fill='#94A7B4')
    d.text((45,1040),'Geometry sample — actual CypCut import and machine cutting still to be checked.',font=font(21),fill='#A6B5C0')
    img.save(EXAMPLES/'laserfont2-preview.png')

def length(path):
    p=sample_path(path,300)
    return sum(math.dist(a,b) for a,b in zip(p,p[1:]))

def svg_master(glyphs,rows):
    width=max(sum(glyphs[c]['advance_mm'] for c in row) for row in rows)+10
    height=35*len(rows)+10
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.4f}mm" height="{height:.4f}mm" viewBox="0 0 {width:.4f} {height:.4f}">',
           '<title>laserfont2 original Bezier master, 20 mm cap height</title>',
           '<desc>Open single-line paths. Two intentional bridges per enclosed counter. No filled lettering.</desc>',
           '<g fill="none" stroke="black" stroke-width="0.15" stroke-linecap="round" stroke-linejoin="round">']
    for row,text in enumerate(rows):
        x=5
        for i,char in enumerate(text):
            g=glyphs[char]
            parts.append(f'<g id="row{row}-char{i}-{ord(char)}" transform="translate({x:.9f},{25+row*35}) scale(1,-1)">')
            for path in g['paths']:
                p=path[0]['p'];cmd=f'M {p[0]:.9f},{p[1]:.9f}'
                for s in path:
                    if s['type']=='LINE':cmd+=f' L {s["q"][0]:.9f},{s["q"][1]:.9f}'
                    else:cmd+=' C '+' '.join(f'{s[k][0]:.9f},{s[k][1]:.9f}' for k in ['c1','c2','q'])
                parts.append(f'<path d="{cmd}"/>')
            parts.append('</g>');x+=g['advance_mm']
    parts.extend(['</g>','</svg>'])
    (EXAMPLES/'laserfont2-master.svg').write_text('\n'.join(parts),encoding='utf-8')
def add_poly_text(msp,glyphs,text,x=0,y=0,height=20,rotation=0):
    if height<=0:raise ValueError('Height must be positive')
    unsupported=sorted(set(text.upper())-set(glyphs))
    if unsupported:raise ValueError('Unsupported characters: '+repr(unsupported))
    offset=0;out=[]
    for char in text.upper():
        g=glyphs[char]
        for path in g['paths_xyb']:
            pts=[]
            for px,py,b in path:
                tx,ty,_=transform((px+offset,py),x,y,height/20,rotation)
                pts.append((tx,ty,b))
            out.append(msp.add_lwpolyline(pts,format='xyb',close=False,dxfattribs={'layer':'ID_CUT_SINGLELINE','const_width':0}))
        offset+=g['advance_mm']
    return out

def build_samples(glyphs):
    EXAMPLES.mkdir(exist_ok=True)
    rows=['ABCDEFGHIJKLM','NOPQRSTUVWXYZ','0123456789-','PANEL-A01','LASER-02','B8-S5-J1-O0']
    for mode in ['bezier','polyline']:
        d=new_drawing();data=glyphs if mode=='bezier' else json.loads((ROOT/'glyphs-v2-polyline.json').read_text())['glyphs']
        fn=add_text if mode=='bezier' else add_poly_text
        for i,txt in enumerate(rows):fn(d.modelspace(),data,txt,0,-35*i)
        d.saveas(EXAMPLES/('laserfont2-alphabet-'+mode+'.dxf'))
        d=new_drawing();fn(d.modelspace(),data,'PANEL-A01',0,0)
        d.saveas(EXAMPLES/('PANEL-A01-H20-'+mode+'.dxf'))
    preview(glyphs);svg_master(glyphs,rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text');p.add_argument('--output',type=Path);p.add_argument('--height',type=float,default=20)
    p.add_argument('--rotation',type=float,default=0);p.add_argument('--x',type=float,default=0);p.add_argument('--y',type=float,default=0)
    p.add_argument('--mode',choices=['bezier','polyline'],default='bezier');p.add_argument('--samples',action='store_true')
    a=p.parse_args();glyphs=json.loads(SOURCE.read_text())['glyphs']
    if a.samples:build_samples(glyphs)
    if a.text is not None:
        if not a.output:p.error('--text requires --output')
        if a.output.exists():p.error('Output exists; choose a new filename')
        d=new_drawing();data=glyphs if a.mode=='bezier' else json.loads((ROOT/'glyphs-v2-polyline.json').read_text())['glyphs']
        fn=add_text if a.mode=='bezier' else add_poly_text
        entities=fn(d.modelspace(),data,a.text,a.x,a.y,a.height,a.rotation)
        d.saveas(a.output)
        print(json.dumps({'output':str(a.output),'cut_paths':len(entities),'units':'mm','height_mm':a.height,'mode':a.mode}))
if __name__=='__main__':main()
