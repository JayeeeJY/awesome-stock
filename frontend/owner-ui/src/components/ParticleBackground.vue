<template>
  <div ref="canvasRef" class="particle-bg" aria-hidden="true" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { tsParticles, type Container } from '@tsparticles/engine'

const canvasRef = ref<HTMLElement>()
let container: Container | undefined
let disposed = false
let motion: MediaQueryList | undefined
function syncMotion() {
  if (!container) return
  const reduced = Boolean(motion?.matches)
  container.actualOptions.particles.move.enable = !reduced
  container.actualOptions.interactivity.events.onHover.enable = !reduced
  container.actualOptions.interactivity.events.onClick.enable = !reduced
  if (reduced) {
    container.pause()
    container.particles.draw({ value: 0, factor: 0 })
  } else container.play()
}

onMounted(async () => {
  motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  motion.addEventListener('change', syncMotion)
  try {
    // Load locally bundled particles only on the login screen.
    const { loadSlim } = await import('@tsparticles/slim')
    if (disposed) return
    await loadSlim(tsParticles)
    if (disposed || !canvasRef.value) return
    const created = await tsParticles.load({
      element: canvasRef.value,
      options: {
        background: { color: { value: 'transparent' } },
        fpsLimit: 60,
        pauseOnBlur: true,
        pauseOnOutsideViewport: false,
        interactivity: {
          events: {
            onHover: { enable: !motion.matches, mode: 'grab' },
            onClick: { enable: !motion.matches, mode: 'push' },
          },
          modes: {
            grab: { distance: 140, links: { opacity: 0.5 } },
            push: { quantity: 3 },
          },
        },
        particles: {
          color: { value: ['#a78bfa', '#818cf8', '#38bdf8', '#ffffff'] },
          links: { color: '#818cf8', distance: 150, enable: true, opacity: 0.18, width: 1 },
          move: { enable: true, speed: 0.8, direction: 'none', outModes: { default: 'bounce' } },
          number: { value: 80, density: { enable: true } },
          opacity: { value: { min: 0.2, max: 0.7 } },
          shape: { type: 'circle' },
          size: { value: { min: 1, max: 3 } },
        },
        detectRetina: true,
      },
    })
    if (disposed) { created?.destroy(); return }
    container = created
    syncMotion()
  } catch {
    // Authentication remains available with the CSS starfield if canvas initialization fails.
  }
})

onUnmounted(() => {
  disposed = true
  motion?.removeEventListener('change', syncMotion)
  container?.destroy()
})
</script>

<style scoped>
.particle-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.particle-bg :deep(canvas) { position: absolute; inset: 0; pointer-events: auto; }
</style>
