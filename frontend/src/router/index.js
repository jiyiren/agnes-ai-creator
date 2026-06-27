import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import ImageView from '../views/ImageView.vue'
import VideoView from '../views/VideoView.vue'

import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'chat', component: ChatView },
  { path: '/chat/:id', name: 'chat-detail', component: ChatView },
  { path: '/images', name: 'images', component: ImageView },
  { path: '/videos', name: 'videos', component: VideoView },
  { path: '/settings', name: 'settings', component: SettingsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
