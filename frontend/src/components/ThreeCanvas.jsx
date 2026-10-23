import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeCanvas({ regime, isScanning }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x04060a, 0.0018);

    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 30, 85);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    // Particle Cloud Geometry (Waves + Ring)
    const particleCount = 4500;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);
    const colors = new Float32Array(particleCount * 3);

    // Color definitions based on regime
    const isBearish = regime?.includes('BEAR') || regime?.includes('PANIC');
    const isBull = regime?.includes('BULL');

    const primaryColor = isBearish 
      ? new THREE.Color(0xf43f5e) 
      : isBull 
        ? new THREE.Color(0x10b981) 
        : new THREE.Color(0x38bdf8);
    
    const secondaryColor = isBearish 
      ? new THREE.Color(0xa855f7) 
      : isBull 
        ? new THREE.Color(0x06b6d4) 
        : new THREE.Color(0xf59e0b);

    for (let i = 0; i < particleCount; i++) {
      // Create a vast organic terrain wave
      const x = (Math.random() - 0.5) * 220;
      const z = (Math.random() - 0.5) * 220;
      const y = Math.sin(x * 0.05) * Math.cos(z * 0.05) * 12;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y - 10;
      positions[i * 3 + 2] = z;

      scales[i] = Math.random() * 2.2 + 0.5;

      const mixFactor = Math.random();
      const mixedColor = primaryColor.clone().lerp(secondaryColor, mixFactor);
      colors[i * 3] = mixedColor.r;
      colors[i * 3 + 1] = mixedColor.g;
      colors[i * 3 + 2] = mixedColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('scale', new THREE.BufferAttribute(scales, 1));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Custom circular soft glow texture for particles
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.6)');
    gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.15)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    const texture = new THREE.CanvasTexture(canvas);

    const material = new THREE.PointsMaterial({
      size: 1.8,
      map: texture,
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Floating 3D Geometric Holographic Wireframe Core (Awwwards Studio signature)
    const torusGeom = new THREE.TorusGeometry(18, 0.6, 16, 100);
    const torusMat = new THREE.MeshBasicMaterial({
      color: primaryColor,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending
    });
    const torus = new THREE.Mesh(torusGeom, torusMat);
    torus.position.set(0, 5, -20);
    torus.rotation.x = Math.PI / 3;
    scene.add(torus);

    const innerIcoGeom = new THREE.IcosahedronGeometry(10, 2);
    const innerIcoMat = new THREE.MeshBasicMaterial({
      color: secondaryColor,
      wireframe: true,
      transparent: true,
      opacity: 0.18,
      blending: THREE.AdditiveBlending
    });
    const innerIco = new THREE.Mesh(innerIcoGeom, innerIcoMat);
    innerIco.position.set(0, 5, -20);
    scene.add(innerIco);

    // Mouse Tracking with smooth lerp
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (e) => {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.05;
      mouseY = (e.clientY - window.innerHeight / 2) * 0.05;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Resize Handler
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth camera motion
      targetX += (mouseX - targetX) * 0.05;
      targetY += (mouseY - targetY) * 0.05;
      camera.position.x = targetX * 0.8;
      camera.position.y = 30 - targetY * 0.5;
      camera.lookAt(0, 5, -20);

      // Rotate 3D Core
      const spinSpeed = isScanning ? 0.025 : 0.005;
      torus.rotation.z += spinSpeed;
      torus.rotation.y += spinSpeed * 0.5;
      innerIco.rotation.x -= spinSpeed * 0.8;
      innerIco.rotation.y -= spinSpeed * 0.8;

      // Organic Wave Motion on Particles
      const posAttr = particles.geometry.attributes.position;
      const waveSpeed = isScanning ? 2.5 : 0.8;
      for (let i = 0; i < particleCount; i++) {
        const x = posAttr.getX(i);
        const z = posAttr.getZ(i);
        const newY = Math.sin((x * 0.06) + (elapsedTime * waveSpeed)) * 
                     Math.cos((z * 0.06) + (elapsedTime * waveSpeed)) * 8 - 10;
        posAttr.setY(i, newY);
      }
      posAttr.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
      if (mount && renderer.domElement) {
        mount.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      texture.dispose();
      renderer.dispose();
    };
  }, [regime, isScanning]);

  return (
    <div 
      ref={mountRef} 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.85
      }} 
    />
  );
}
