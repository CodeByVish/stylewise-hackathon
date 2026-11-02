import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Box3, Vector3 } from 'three';
import { createRequest, fixtureBody, previewReport, parseReport, fixtureCatalog, parseCatalog } from '../src/lib/fit-contract.ts';

for (const size of ['S', 'M']) {
  const report = previewReport(createRequest(fixtureBody, size, 'none'));
  assert.deepEqual(report.easeCm, size === 'S' ? { chest: -4, waist: -2 } : { chest: 8, waist: 10 });
  assert.deepEqual(parseReport(JSON.parse(JSON.stringify(report))), report);
}
const valid = previewReport(createRequest(fixtureBody, 'M', 'none'));
for (const patch of [{version:'2'}, {easeCm:{chest:'8',waist:10}}, {bodyMeshUrl:'https://example.com/body.glb'}, {garmentMeshUrl:'//example.com/top.glb'}, {warnings:42}, {measurementsCm:{...fixtureBody,chest:-5}}]) {
  assert.throws(() => parseReport({...valid,...patch}));
}
const preference = previewReport(createRequest(fixtureBody, 'M', 'front-opening'));
assert(preference.unknowns.includes('Front-opening construction is unverified'));
assert.deepEqual(parseCatalog(fixtureCatalog), fixtureCatalog);
assert.throws(() => parseCatalog({ ...fixtureCatalog, source: '' }));
assert.throws(() => parseCatalog({ ...fixtureCatalog, sizes: { S: { chestCm: -1 } } }));
const custom = { ...fixtureCatalog, source: 'Team-provided source', sizes: { ...fixtureCatalog.sizes, M: { ...fixtureCatalog.sizes.M, chestCm: 100 } } };
assert.equal(previewReport(createRequest(fixtureBody, 'M', 'none', custom)).easeCm.chest, 10);
assert.equal(previewReport(createRequest(fixtureBody, 'M', 'none', custom)).provenance, custom.source);
const loader = new GLTFLoader();
for (const name of ['body', 'top-s', 'top-m']) {
  const bytes = await readFile(`public/fixtures/${name}.glb`);
  const gltf = await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  const box = new Box3().setFromObject(gltf.scene); const size = box.getSize(new Vector3());
  assert(!box.isEmpty()); assert([size.x,size.y,size.z].every(n => Number.isFinite(n) && n > 0 && n < 3));
  let meshes=0; gltf.scene.traverse(object => { if (object.isMesh) { meshes++; assert(object.geometry.getAttribute('position').count > 0); } });
  assert(meshes > 0);
  if (name.startsWith('top-')) {
    const torso = gltf.scene.getObjectByName('calibrated-torso');
    assert(torso?.isMesh);
    const positions = torso.geometry.getAttribute('position');
    const { verticesPerRing, chest, waist } = torso.userData.measurementRings;
    for (const [ring, target] of [[chest, name === 'top-s' ? 86 : 98], [waist, name === 'top-s' ? 72 : 84]]) {
      let circumference = 0;
      for (let i = 0; i < verticesPerRing - 1; i++) {
        const a = new Vector3().fromBufferAttribute(positions, ring * verticesPerRing + i);
        const b = new Vector3().fromBufferAttribute(positions, ring * verticesPerRing + i + 1);
        circumference += a.distanceTo(b) * 100;
      }
      assert(Math.abs(circumference - target) < 0.01, `${name} circumference ${circumference} vs ${target}`);
    }
  }
}
console.log('Passed: S/M arithmetic, report validation, preference uncertainty, and three GLB assets. Browser visual QA remains required.');
