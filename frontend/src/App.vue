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
            <h1 class="font-extrabold text-lg leading-tight bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
              Agnes AI Creator
            </h1>
            <p class="text-xs text-white/50 mt-0.5">多模态 Web 客户端</p>
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
        <p class="text-xs text-white/40 text-center flex items-center justify-center gap-1.5 flex-wrap">
          <a
            href="https://github.com/jiyiren/agnes-ai-creator"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1.5 text-white/50 hover:text-cyan-300 transition-colors"
          >
            <svg class="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            Agnes AI Creator
          </a>
          <span>· 开源项目</span>
        </p>
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
