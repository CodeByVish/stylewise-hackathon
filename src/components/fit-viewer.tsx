'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export type View = 'front' | 'side' | 'back' | 'quarter';
// camera angle around the figure (degrees from the front)
const VIEW_ANGLE: Record<View, number> = { front: 0, quarter: 35, side: 90, back: 180 };
const SKIN_TONES = ['#5b382b', '#80533f', '#ad7658', '#c79370', '#ddb99d'];

export default function FitViewer({ bodyUrl, garmentUrl, view, rotating, showBody, combined = false, skinTone }: {
  bodyUrl: string; garmentUrl?: string; combined?: boolean; view: View; rotating: boolean; showBody: boolean; skinTone?: string;
}) {
  const resolvedSkinTone = skinTone ?? SKIN_TONES[[...bodyUrl].reduce((sum, char) => sum + char.charCodeAt(0), 0) % SKIN_TONES.length];
  const host = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const frameRef = useRef<((view: View) => void) | null>(null);
  const bodyRef = useRef<THREE.Object3D | null>(null);
  const options = useRef({ rotating, showBody, view });
  const [status, setStatus] = useState('Loading 3D assets…');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    options.current = { rotating, showBody, view };
    if (bodyRef.current) bodyRef.current.visible = showBody;
    if (controlsRef.current) controlsRef.current.autoRotate = rotating;
  }, [rotating, showBody, view]);
  useEffect(() => {
    bodyRef.current?.traverse(child => {
      if (!(child instanceof THREE.Mesh) || !child.userData.bodySurface) return;
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach(material => {
        if (material instanceof THREE.MeshStandardMaterial) material.color.set(resolvedSkinTone);
      });
    });
  }, [resolvedSkinTone]);
  useEffect(() => {
    const camera = cameraRef.current, controls = controlsRef.current;
    if (!camera || !controls) return;
    frameRef.current?.(view);
  }, [view]);
  useEffect(() => {
    const container = host.current;
    if (!container) return;
    let disposed = false, frame = 0;
    const scene = new THREE.Scene();
    const disposeObject = (object: THREE.Object3D) => object.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose();
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        materials.forEach(material => { Object.values(material).forEach(value => { if (value instanceof THREE.Texture) value.dispose(); }); material.dispose(); });
      }
    });
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch { queueMicrotask(() => { if (!disposed) { setFailed(true); setStatus('3D rendering is unavailable on this device. Size comparisons remain available.'); } }); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    // studio look: filmic tone mapping + soft image-based light instead of strong raw lights
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(37, 1, 0.01, 50);
    const initial = options.current.view;
    const a0 = THREE.MathUtils.degToRad(VIEW_ANGLE[initial]);
    camera.position.set(2.8 * Math.sin(a0), 1.1, 2.8 * Math.cos(a0));
    cameraRef.current = camera;
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.9, 0); controls.enableDamping = true;
    controls.minDistance = 1.5; controls.maxDistance = 4.5; controls.maxPolarAngle = Math.PI * 0.75;
    controls.enablePan = false; controls.autoRotateSpeed = 1.3; controls.autoRotate = options.current.rotating;
    controlsRef.current = controls;
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; scene.environment = envMap;
    scene.add(new THREE.HemisphereLight('#fffaf2', '#b9b8ad', 0.5));
    const key = new THREE.DirectionalLight('#fff6ec', 1.6); key.position.set(1.8, 4, 3); key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -0.0004;
    Object.assign(key.shadow.camera, { left: -1.2, right: 1.2, top: 2.2, bottom: -0.2, near: 0.5, far: 10 }); scene.add(key);
    const rim = new THREE.DirectionalLight('#ffffff', 0.7); rim.position.set(-3, 2.5, -3); scene.add(rim);
    // soft contact shadow so the figure stands on the platform instead of floating
    const catcher = new THREE.Mesh(new THREE.CircleGeometry(0.9, 64), new THREE.ShadowMaterial({ opacity: 0.18 }));
    catcher.rotation.x = -Math.PI / 2; catcher.position.y = 0.006; catcher.receiveShadow = true; scene.add(catcher);
    const platform = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.38, 0.035, 80), new THREE.MeshStandardMaterial({ color: '#dad9cd', roughness: 1 }));
    platform.position.y = -0.013; scene.add(platform);
    const frameCamera = (direction: View) => {
      const bounds = new THREE.Box3().setFromObject(scene);
      const extent = bounds.getSize(new THREE.Vector3());
      if (extent.y < 0.1) return;
      const center = bounds.getCenter(new THREE.Vector3());
      const halfFov = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      const horizontal = Math.max(extent.x, extent.z);
      // same framing for every view: full figure with a small margin
      const distance = Math.max(extent.y / (2 * halfFov), horizontal / (2 * halfFov * camera.aspect)) * 1.1;
      const a = THREE.MathUtils.degToRad(VIEW_ANGLE[direction]);
      controls.target.set(center.x, center.y, center.z);
      camera.position.set(center.x + distance * Math.sin(a), center.y + 0.03, center.z + distance * Math.cos(a));
      controls.minDistance = distance * 0.45; controls.maxDistance = distance * 2.5;
      controls.update();
    };
    frameRef.current = frameCamera;
    const resize = () => { const { width, height } = container.getBoundingClientRect(); renderer.setSize(width, height); camera.aspect = width / Math.max(height, 1); camera.updateProjectionMatrix(); frameCamera(options.current.view); };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    queueMicrotask(() => { if (!disposed) { setFailed(false); setStatus('Loading 3D assets…'); } });
    const loader = new GLTFLoader();
    const addHairCap = (root: THREE.Object3D) => {
      const bounds = new THREE.Box3().setFromObject(root);
      const size = bounds.getSize(new THREE.Vector3());
      const center = bounds.getCenter(new THREE.Vector3());
      if (size.y < 0.1) return;
      const radius = 0.064 * size.y;
      const geometry = new THREE.SphereGeometry(radius, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.63);
      geometry.scale(1, 1.12, 1.04);
      const material = new THREE.MeshStandardMaterial({ color: '#352820', roughness: 0.92, metalness: 0 });
      const cap = new THREE.Mesh(geometry, material);
      cap.name = 'neutral molded hair';
      cap.position.set(center.x, bounds.max.y - 0.066 * size.y, center.z - 0.006 * size.y);
      cap.castShadow = true; cap.receiveShadow = true;
      root.add(cap);
    };
    const load = async (url: string, isBody: boolean) => {
      const gltf = await loader.loadAsync(url);
      if (disposed) { disposeObject(gltf.scene); return; }
      if (isBody) {
        bodyRef.current = combined ? gltf.scene.getObjectByName('body') || gltf.scene : gltf.scene;
        bodyRef.current.traverse(child => {
          if (!(child instanceof THREE.Mesh)) return;
          child.userData.bodySurface = true;
          child.material = Array.isArray(child.material)
            ? child.material.map(material => material.clone())
            : child.material.clone();
          const materials = Array.isArray(child.material) ? child.material : [child.material];
          // an engine scene already carries its finish, underwear and moulded hair
          if (!combined) materials.forEach(material => {
            if (material instanceof THREE.MeshStandardMaterial) material.color.set(resolvedSkinTone);
          });
        });
        if (!combined) addHairCap(bodyRef.current);
        bodyRef.current.visible = options.current.showBody;
      }
      gltf.scene.traverse(child => {
        if (!(child instanceof THREE.Mesh)) return;
        child.castShadow = true; child.receiveShadow = true;
        const material = child.material as THREE.MeshStandardMaterial;
        if (material && 'envMapIntensity' in material) material.envMapIntensity = 0.85;
      });
      scene.add(gltf.scene); frameCamera(options.current.view);
    };
    Promise.all([load(bodyUrl, true), ...(garmentUrl ? [load(garmentUrl, false)] : [])]).then(() => {
      if (!disposed) setStatus('');
    }).catch(() => { if (!disposed) { setFailed(true); setStatus('Could not load these 3D assets. Check the mesh paths or return to the fixture.'); } });
    const animate = () => { frame = requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }; animate();
    const lost = (event: Event) => { event.preventDefault(); setFailed(true); setStatus('The 3D context was lost. Reload to restore the viewer.'); };
    renderer.domElement.addEventListener('webglcontextlost', lost);
    return () => {
      disposed = true; cancelAnimationFrame(frame); observer.disconnect(); controls.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', lost);
      disposeObject(scene); envMap.dispose(); pmrem.dispose(); renderer.dispose(); renderer.domElement.remove();
      cameraRef.current = null; controlsRef.current = null; frameRef.current = null; bodyRef.current = null;
    };
  }, [bodyUrl, garmentUrl, combined, resolvedSkinTone]);
  return <><div ref={host} className="canvas-host" role="img" aria-label={`Interactive 3D outfit, ${view} view. Use the view buttons for keyboard navigation.`} />{status && <div className={`viewer-status ${failed ? 'error' : ''}`} role="status">{status}</div>}</>;
}
