'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export type View = 'front' | 'side' | 'back';
export default function FitViewer({ bodyUrl, garmentUrl, view, rotating, showBody, combined = false }: {
  bodyUrl: string; garmentUrl?: string; combined?: boolean; view: View; rotating: boolean; showBody: boolean;
}) {
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
    container.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(37, 1, 0.01, 50);
    const initial = options.current.view;
    camera.position.set(initial === 'side' ? 2.8 : 0, 1.1, initial === 'front' ? 2.8 : initial === 'back' ? -2.8 : 0);
    cameraRef.current = camera;
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.9, 0); controls.enableDamping = true;
    controls.minDistance = 1.5; controls.maxDistance = 4.5; controls.maxPolarAngle = Math.PI * 0.75;
    controls.enablePan = false; controls.autoRotateSpeed = 1.3; controls.autoRotate = options.current.rotating;
    controlsRef.current = controls;
    scene.add(new THREE.HemisphereLight('#fff8ee', '#9b9b8b', 3));
    const key = new THREE.DirectionalLight('#fffaf4', 3); key.position.set(3, 4, 5); scene.add(key);
    const rim = new THREE.DirectionalLight('#ffffff', 2); rim.position.set(-3, 2, -3); scene.add(rim);
    const platform = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.38, 0.035, 80), new THREE.MeshStandardMaterial({ color: '#dad9cd', roughness: 1 }));
    platform.position.y = -0.013; scene.add(platform);
    const frameCamera = (direction: View) => {
      const bounds = new THREE.Box3().setFromObject(scene);
      const extent = bounds.getSize(new THREE.Vector3());
      if (extent.y < 0.1) return;
      const center = bounds.getCenter(new THREE.Vector3());
      const halfFov = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      const horizontal = direction === 'side' ? extent.z : extent.x;
      const distance = Math.max(extent.y / (2 * halfFov), horizontal / (2 * halfFov * camera.aspect)) * 1.12;
      controls.target.set(center.x, center.y, center.z);
      camera.position.set(center.x + (direction === 'side' ? distance : 0), center.y + 0.03, center.z + (direction === 'back' ? -distance : direction === 'front' ? distance : 0));
      controls.minDistance = distance * 0.45; controls.maxDistance = distance * 2.5;
      controls.update();
    };
    frameRef.current = frameCamera;
    const resize = () => { const { width, height } = container.getBoundingClientRect(); renderer.setSize(width, height); camera.aspect = width / Math.max(height, 1); camera.updateProjectionMatrix(); frameCamera(options.current.view); };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    queueMicrotask(() => { if (!disposed) { setFailed(false); setStatus('Loading 3D assets…'); } });
    const loader = new GLTFLoader();
    const load = async (url: string, isBody: boolean) => {
      const gltf = await loader.loadAsync(url);
      if (disposed) { disposeObject(gltf.scene); return; }
      if (isBody) { bodyRef.current = combined ? gltf.scene.getObjectByName('body') || gltf.scene : gltf.scene; bodyRef.current.visible = options.current.showBody; }
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
      disposeObject(scene); renderer.dispose(); renderer.domElement.remove();
      cameraRef.current = null; controlsRef.current = null; frameRef.current = null; bodyRef.current = null;
    };
  }, [bodyUrl, garmentUrl, combined]);
  return <><div ref={host} className="canvas-host" role="img" aria-label={`Interactive 3D outfit, ${view} view. Use the view buttons for keyboard navigation.`} />{status && <div className={`viewer-status ${failed ? 'error' : ''}`} role="status">{status}</div>}</>;
}
