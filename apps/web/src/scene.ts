namespace HF {
  type Vec3=[number,number,number];
  interface Face {points:Vec3[];fill:string;stroke?:string;depth?:number}
  interface SceneAsset {id:string;x:number;z:number;label:string}
  /** Small original orthographic software-3D renderer. Real 3D vertices and
   * camera transforms, rendered to Canvas2D; no WebGL/CDN/runtime package.
   * Energy links are conceptual, not solved branch power flows. */
  export function mountEnergyScene(canvas:HTMLCanvasElement,system:HybridSystem,reduced:boolean,onSelect:(id:string)=>void):()=>void {
    const ctx=canvas.getContext('2d');if(!ctx)return ()=>{};
    let yaw=-.57,pitch=.55,zoom=1,frame=0,disposed=false,visible=true,drag=false,moved=false,lastX=0,lastY=0,lastTime=0;
    let width=0,height=0,phase=0,dirty=true;
    const pos:Vec3[]=[[-1.7,0,1.0],[-1.9,0,-1.15],[.45,0,1.25],[.5,0,-1.15],[2.3,0,.8],[2.2,0,-1.35],[-.45,0,.1]];
    const ids=[...system.technologies,'load',...(system.topology==='Off-grid'?[]:['grid'])];
    const assets:SceneAsset[]=ids.map((id,i)=>({id,x:pos[i%pos.length]![0],z:pos[i%pos.length]![2],label:techById(id).name}));
    let hit:{id:string;x:number;y:number}[]=[];
    const projection=(v:Vec3):[number,number,number]=>{
      const rx=v[0]*Math.cos(yaw)+v[2]*Math.sin(yaw),rz=-v[0]*Math.sin(yaw)+v[2]*Math.cos(yaw);
      const scale=Math.min(width/7.8,height/6.0)*zoom;
      return [width*.5+rx*scale,height*.62+(-v[1]*Math.cos(pitch)+rz*Math.sin(pitch))*scale,v[1]*Math.sin(pitch)+rz*Math.cos(pitch)];
    };
    function draw():void {
      if(!ctx||width===0)return;
      ctx.clearRect(0,0,width,height);
      const background=ctx.createRadialGradient(width*.48,height*.6,15,width*.48,height*.6,width*.6);
      background.addColorStop(0,'#172a2b');background.addColorStop(1,'#0d171d');ctx.fillStyle=background;ctx.fillRect(0,0,width,height);
      const faces:Face[]=[];
      const face=(points:Vec3[],fill:string,stroke?:string):void=>{faces.push({points,fill,stroke});};
      function cube(x:number,y:number,z:number,w:number,h:number,d:number,colors:[string,string,string]):void {
        const a:Vec3=[x-w/2,y,z-d/2],b:Vec3=[x+w/2,y,z-d/2],c:Vec3=[x+w/2,y,z+d/2],e:Vec3=[x-w/2,y,z+d/2];
        const up=(v:Vec3):Vec3=>[v[0],v[1]+h,v[2]];
        face([a,b,up(b),up(a)],colors[2]);face([b,c,up(c),up(b)],colors[1]);
        face([c,e,up(e),up(c)],colors[2]);face([e,a,up(a),up(e)],colors[1]);face([up(a),up(b),up(c),up(e)],colors[0]);
      }
      function cylinder(x:number,z:number,h:number,color:string):void {
        const ring:Vec3[]=[];
        for(let i=0;i<12;i++){const a=i*Math.PI/6,b=(i+1)*Math.PI/6;const p:Vec3=[x+.26*Math.cos(a),.2,z+.26*Math.sin(a)],q:Vec3=[x+.26*Math.cos(b),.2,z+.26*Math.sin(b)];
          face([p,q,[q[0],h,q[2]],[p[0],h,p[2]]],i%3===0?'#8e76b0':color);ring.push([p[0],h,p[2]]);}
        face(ring,'#e0caff');
      }
      // Raised base and ground-plane grid.
      cube(0,-.15,0,6.25,.15,4.45,['#1a3033','#132226','#101e24']);
      for(let x=-3;x<=3;x+=.5)face([[x,.005,-2.1],[x+.008,.005,-2.1],[x+.008,.005,2.1],[x,.005,2.1]],'#284345');
      for(let z=-2;z<=2;z+=.5)face([[-3,.005,z],[3,.005,z],[3,.005,z+.008],[-3,.005,z+.008]],'#284345');
      for(const a of assets){
        const {id,x,z}=a,tech=techById(id);
        cube(x,.02,z,1.26,.09,1.02,['#304449','#24353d','#1b2b31']);
        if(id==='solar'||id==='csp'){
          for(let row=0;row<2;row++)for(let col=0;col<3;col++){
            const px=x-.49+col*.34,pz=z-.38+row*.43;
            cube(px+.14,.12,pz+.17,.025,.22,.025,['#d5e7ef','#607b8e','#435d70']);
            face([[px,.40,pz],[px+.30,.40,pz],[px+.30,.23,pz+.35],[px,.23,pz+.35]],'#36658b','#85bdda');
            face([[px+.145,.40,pz],[px+.151,.40,pz],[px+.151,.23,pz+.35],[px+.145,.23,pz+.35]],'#9ecdd7');
          }
        }else if(id==='wind'){
          cube(x,.1,z,.075,1.9,.075,['#e4edf2','#a6c2cc','#779ba8']);
          cube(x,1.96,z,.24,.18,.19,['#f1f7f8','#b4cad0','#88a9b5']);
          for(let j=0;j<3;j++){
            const ang=phase+j*Math.PI*2/3;
            const vx=Math.cos(ang),vy=Math.sin(ang);
            face([[x-vy*.05,2+vx*.05,z+.15],[x+vx*.94-vy*.028,2+vy*.94+vx*.028,z+.15],[x+vx*.55+vy*.07,2+vy*.55-vx*.07,z+.15]],'#e1f1f3','#94cad9');
          }
        }else if(id==='battery'){
          cube(x,.12,z,1.06,.58,.65,['#c5ed9e','#66864b','#8cab65']);
          for(let k=0;k<8;k++)cube(x-.45+k*.125,.16,z+.332,.025,.49,.016,['#90b272','#4b6639','#597e43']);
          cube(x-.52,.18,z,.013,.36,.38,['#102329','#162b2d','#1a3535']);
          cube(x-.529,.36,z-.08,.02,.09,.12,['#b9fa8b','#b9fa8b','#b9fa8b']);
        }else if(['hydrogen','electrolyzer','fuelcell'].includes(id)){
          cylinder(x-.3,z,.92,'#b49ad3');cylinder(x+.3,z,.92,'#bca5d7');
          cube(x,.11,z+.32,.92,.15,.17,['#d5b8ff','#746281','#806c93']);
        }else if(id==='load'){
          cube(x,.12,z,.82,1.05,.68,['#708998','#314651','#3f5663']);
          cube(x,.12,z+.32,1.0,.22,.2,['#8a9ea7','#425967','#506d7b']);
          for(let k=0;k<3;k++)for(let j=0;j<3;j++)cube(x-.28+k*.25,.38+j*.24,z+.35,.12,.12,.018,['#91d8de','#91d8de','#a9e2de']);
          cube(x,1.18,z,.38,.09,.30,['#c9d9d9','#879e9f','#718d91']);
        }else if(id==='grid'||id==='network'){
          cube(x-.15,.1,z,.035,1.25,.035,['#d5dfda','#9baca8','#738b8b']);cube(x+.15,.1,z,.035,1.25,.035,['#d5dfda','#9baca8','#738b8b']);
          cube(x,1.10,z,.70,.055,.055,['#cadad7','#91aaa7','#718b89']);cube(x,.77,z,.53,.04,.04,['#cadad7','#91aaa7','#718b89']);
          cube(x,.12,z,.6,.4,.48,['#b9ccc4','#637f7e','#789592']);
        }else if(['hydro','pumpedhydro','tidal','wave'].includes(id)){
          cube(x,.12,z,.99,.16,.75,['#599dc1','#376582','#437c96']);
          for(let j=0;j<3;j++)cube(x-.33+j*.33,.29,z,.09,.42,.56,['#bbcfd7','#698998','#819da8']);
        }else{
          cube(x,.12,z,.92,.6,.68,[tech.color,'#536074','#727b90']);
          for(let j=0;j<3;j++)cube(x-.29+j*.3,.74,z,.11,.25,.12,['#d5dae1','#8994a2','#647180']);
        }
      }
      faces.forEach(f=>f.depth=f.points.reduce((s,v)=>s+projection(v)[2],0)/f.points.length);
      faces.sort((a,b)=>(a.depth??0)-(b.depth??0));
      for(const f of faces){ctx.beginPath();f.points.forEach((v,i)=>{const [x,y]=projection(v);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.closePath();ctx.fillStyle=f.fill;ctx.fill();if(f.stroke){ctx.strokeStyle=f.stroke;ctx.lineWidth=.7;ctx.stroke();}}
      // Schematic connector route overlays; these are NOT numerical branch flows.
      for(const a of assets){const b=projection([a.x,.11,a.z]),hub=projection([.05,.11,.05]);
        ctx.strokeStyle=techById(a.id).color+'66';ctx.lineWidth=1;ctx.setLineDash([3,5]);ctx.beginPath();ctx.moveTo(b[0],b[1]);ctx.lineTo(hub[0],hub[1]);ctx.stroke();ctx.setLineDash([]);
        if(!reduced){const k=(phase*.20)%1;ctx.fillStyle=techById(a.id).color;ctx.beginPath();ctx.arc(b[0]+(hub[0]-b[0])*k,b[1]+(hub[1]-b[1])*k,2.2,0,Math.PI*2);ctx.fill();}
      }
      hit=[];ctx.font='500 10px "Segoe UI",sans-serif';ctx.textAlign='center';
      for(const a of assets){const p=projection([a.x,.08,a.z+.75]),w=ctx.measureText(a.label).width+19;
        ctx.fillStyle='#101e28e8';ctx.beginPath();ctx.roundRect(p[0]-w/2,p[1]-9,w,20,5);ctx.fill();ctx.fillStyle=techById(a.id).color;ctx.fillText(a.label,p[0],p[1]+5);hit.push({id:a.id,x:p[0],y:p[1]-20});}
    }
    const resize=():void=>{const rect=canvas.getBoundingClientRect();width=rect.width;height=rect.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);dirty=true;draw();};
    const observer=new ResizeObserver(resize);observer.observe(canvas);
    const intersection=new IntersectionObserver(e=>{visible=e[0]?.isIntersecting??true;dirty=true;});intersection.observe(canvas);
    const down=(e:PointerEvent):void=>{drag=true;moved=false;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);};
    const move=(e:PointerEvent):void=>{if(!drag)return;const dx=e.clientX-lastX,dy=e.clientY-lastY;if(Math.abs(dx)+Math.abs(dy)>2)moved=true;yaw+=dx*.006;pitch=clamp(pitch+dy*.002,.25,1.05);lastX=e.clientX;lastY=e.clientY;dirty=true;draw();};
    const up=(e:PointerEvent):void=>{drag=false;if(!moved){const rect=canvas.getBoundingClientRect();const x=e.clientX-rect.left,y=e.clientY-rect.top;const nearest=[...hit].sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];if(nearest&&Math.hypot(nearest.x-x,nearest.y-y)<70)onSelect(nearest.id);}};
    const key=(e:KeyboardEvent):void=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','Home'].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft')yaw-=.15;if(e.key==='ArrowRight')yaw+=.15;if(e.key==='ArrowUp')pitch=clamp(pitch+.1,.25,1.05);if(e.key==='ArrowDown')pitch=clamp(pitch-.1,.25,1.05);if(e.key==='+')zoom=clamp(zoom+.1,.7,1.4);if(e.key==='-')zoom=clamp(zoom-.1,.7,1.4);if(e.key==='Home'){yaw=-.57;pitch=.55;zoom=1;}dirty=true;draw();}};
    const command=(e:Event):void=>{const cmd=(e as CustomEvent<string>).detail;key(new KeyboardEvent('keydown',{key:cmd}));};
    canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);canvas.addEventListener('keydown',key);canvas.addEventListener('scene-command',command);
    function tick(time:number):void{if(disposed)return;if(visible&&!document.hidden&&(dirty||!reduced)&&time-lastTime>40){phase+=reduced?0:.025;draw();lastTime=time;dirty=false;}frame=requestAnimationFrame(tick);}
    resize();frame=requestAnimationFrame(tick);
    return ()=>{disposed=true;cancelAnimationFrame(frame);observer.disconnect();intersection.disconnect();canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',up);canvas.removeEventListener('keydown',key);canvas.removeEventListener('scene-command',command);};
  }
}
