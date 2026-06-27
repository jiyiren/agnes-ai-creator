<script setup>
import { useDialog } from '../composables/useDialog'

const { state, handleConfirm, handleCancel } = useDialog()

const iconMap = {
  confirm: '⚠️',
  alert: '💡',
}

const variantClass = {
  primary: 'btn-primary',
  danger: 'btn-danger',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="state.visible"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
        @click.self="state.type === 'confirm' ? handleCancel() : handleConfirm()"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

        <div class="relative w-full max-w-md glass-strong rounded-3xl p-6 shadow-glow animate-float">
          <div class="flex items-start gap-4">
            <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-fuchsia-500/30 to-cyan-400/30 flex items-center justify-center text-2xl flex-shrink-0 border border-white/20">
              {{ iconMap[state.type] || '💬' }}
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="text-lg font-bold text-white mb-2">{{ state.title }}</h3>
              <p class="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">{{ state.message }}</p>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              v-if="state.type === 'confirm'"
              @click="handleCancel"
              class="btn-ghost px-6"
            >
              {{ state.cancelText }}
            </button>
            <button
              @click="handleConfirm"
              :class="variantClass[state.confirmVariant] || 'btn-primary'"
              class="px-6"
            >
              {{ state.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.25s ease;
}
.dialog-enter-active .relative,
.dialog-leave-active .relative {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
.dialog-enter-from .relative,
.dialog-leave-to .relative {
  transform: scale(0.92) translateY(8px);
  opacity: 0;
}
</style>
