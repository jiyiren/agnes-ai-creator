<script setup>
import { useRoute } from 'vue-router'
import AppDialog from './components/AppDialog.vue'

const route = useRoute()

const navItems = [
  { path: '/chat', label: '文本对话', icon: '💬', gradient: 'from-violet-500 to-fuchsia-500' },
  { path: '/images', label: '图片生成', icon: '🎨', gradient: 'from-pink-500 to-orange-400' },
  { path: '/videos', label: '视频生成', icon: '🎬', gradient: 'from-cyan-400 to-blue-500' },
  { path: '/settings', label: '设置', icon: '⚙️', gradient: 'from-slate-400 to-zinc-500' },
]
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <AppDialog />

    <!-- Sidebar -->
    <aside class="w-72 flex-shrink-0 glass-sidebar rounded-r-3xl flex flex-col m-2 mr-0">
      <div class="p-6 border-b border-white/10">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-fuchsia-500 via-violet-500 to-cyan-400 flex items-center justify-center text-xl font-extrabold shadow-glow">
            A
          </div>
          <div>
            <h1 class="font-extrabold text-xl leading-tight bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
              Agnes AI
            </h1>
            <p class="text-xs text-white/50 mt-0.5">多模态 AI 平台</p>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-4 space-y-2">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="route.path.startsWith(item.path) ? 'nav-item-active' : 'nav-item-inactive'"
        >
          <span
            class="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
            :class="route.path.startsWith(item.path)
              ? `bg-gradient-to-br ${item.gradient} shadow-glow-cyan`
              : 'bg-white/10'"
          >
            {{ item.icon }}
          </span>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="p-5 border-t border-white/10">
        <p class="text-xs text-white/40 text-center">©2026 大吉·海趣社. All Rights Reserved.</p>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-hidden p-2 pl-0">
      <div class="h-full glass rounded-3xl overflow-hidden">
        <router-view />
      </div>
    </main>
  </div>
</template>
