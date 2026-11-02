import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { mkdir, writeFile } from 'node:fs/promises';
// GLTFExporter uses FileReader in browsers. Only its binary read is needed here.
globalThis.FileReader = class {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then(result => { this.result = result; this.onloadend?.(); }); }
};
const skin = new THREE.MeshStandardMaterial({ color: '#c1afa0', roughness: 0.9 });
function ellipsoid(group, radius, position, scale) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 24), skin);
  mesh.position.set(...position); mesh.scale.set(...scale); group.add(mesh);
}
const body = new THREE.Group(); body.name = 'Illustrative fixed mannequin — not measurement fitted';
ellipsoid(body, 1, [0, 1.65, 0], [0.087, 0.115, 0.09]);
ellipsoid(body, 1, [0, 1.25, 0], [0.145, 0.27, 0.095]);
ellipsoid(body, 1, [0, 0.95, 0], [0.16, 0.17, 0.105]);
ellipsoid(body, 1, [0, 1.49, 0], [0.054, 0.08, 0.055]);
for (const s of [-1, 1]) {
  ellipsoid(body, 1, [s * 0.092, 0.55, 0], [0.073, 0.4, 0.08]);
  ellipsoid(body, 1, [s * 0.092, 0.12, 0.035], [0.06, 0.11, 0.12]);
  ellipsoid(body, 1, [s * 0.224, 1.19, 0], [0.055, 0.29, 0.058]);
  ellipsoid(body, 1, [s * 0.243, 0.89, 0], [0.045, 0.07, 0.035]);
}
function top(size) {
  const group = new THREE.Group(); group.name = `Original synthetic top ${size} — calibrated polygon chest and waist`;
  const material = new THREE.MeshStandardMaterial({ color: '#768275', roughness: 0.94, side: THREE.DoubleSide });
  // Scale each elliptical polygon so its actual perimeter equals the fixture specification.
  const n = 64;
  const ellipse = (cm) => {
    const ratio = 0.68;
    let perimeter = 0;
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2, b = (i + 1) / n * Math.PI * 2;
      perimeter += Math.hypot(Math.cos(b) - Math.cos(a), ratio * (Math.sin(b) - Math.sin(a)));
    }
    const x = cm / 100 / perimeter;
    return [x, x * ratio];
  };
  const [chestX, chestZ] = ellipse(size === 'S' ? 86 : 98);
  const [waistX, waistZ] = ellipse(size === 'S' ? 72 : 84);
  const width = chestX;
  const rings = [[0.91, waistX * 1.08, waistZ * 1.08], [1.06, waistX, waistZ], [1.30, chestX, chestZ], [1.43, chestX * 1.05, chestZ * 0.92], [1.49, 0.065, 0.064]];
  const vertices = [], indices = [];
  rings.forEach(([y, x, z]) => { for (let i=0;i<=n;i++) { const a=i/n*Math.PI*2; vertices.push(Math.cos(a)*x,y,Math.sin(a)*z); } });
  for (let r=0;r<rings.length-1;r++) for(let i=0;i<n;i++) { const a=r*(n+1)+i,b=a+n+1; indices.push(a,b,a+1,b,b+1,a+1); }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3)); geometry.setIndex(indices); geometry.computeVertexNormals();
  const torso = new THREE.Mesh(geometry,material);
  torso.name = 'calibrated-torso';
  torso.userData.measurementRings = { waist: 1, chest: 2, verticesPerRing: n + 1 };
  group.add(torso);
  for(const s of [-1,1]) {
    const sleeve=new THREE.Mesh(new THREE.CylinderGeometry(0.076,0.084,0.19,32,1,true),material);
    sleeve.position.set(s*(width+0.048),1.365,0); sleeve.rotation.z=s*0.95; group.add(sleeve);
  }
  return group;
}
await mkdir('public/fixtures',{recursive:true});
for(const [name, object] of [['body',body],['top-s',top('S')],['top-m',top('M')]]) {
  const scene=new THREE.Scene(); scene.add(object);
  const result=await new GLTFExporter().parseAsync(scene,{binary:true});
  await writeFile(`public/fixtures/${name}.glb`,Buffer.from(result));
}
console.log('Generated three original illustrative GLB fixtures. Units: meters; +Y up; ground y=0.');
