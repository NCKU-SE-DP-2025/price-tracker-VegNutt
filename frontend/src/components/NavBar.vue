<template>
  <nav class="navbar">
    <div class="title">
      <RouterLink to="/overview">價格追蹤小幫手</RouterLink>
    </div>

    <!-- Hamburger menu for mobile -->
    <div class="hamburger" @click="toggleMenu">
      <span :class="{ 'open': menuOpen }"></span>
      <span :class="{ 'open': menuOpen }"></span>
      <span :class="{ 'open': menuOpen }"></span>
    </div>

    <ul :class="{ 'options': true, 'open': menuOpen }">
      <li><RouterLink to="/overview">物價概覽</RouterLink></li>
      <li><RouterLink to="/trending">物價趨勢</RouterLink></li>
      <li><RouterLink to="/news">相關新聞</RouterLink></li>
      <li v-if="!isLoggedIn"><RouterLink to="/login">登入</RouterLink></li>
      <li v-else @click="logout">Hi, {{ getUserName }}! 登出</li>
    </ul>
  </nav>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useAuthStore } from '@/stores/auth';

// store
const userStore = useAuthStore();
const isLoggedIn = computed(() => userStore.isLoggedIn);
const getUserName = computed(() => userStore.getUserName);

// hamburger state
const menuOpen = ref(false);
function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

// logout method
function logout() {
  userStore.logout();
}
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f3f3f3;
  padding: 1.5em;
  height: 4.5em;
  width: 100%;
  box-shadow: 0 0 5px #000000;
  position: relative;
}

.title > a {
  font-size: 1.4em;
  font-weight: bold;
  color: #2c3e50 !important;
  text-decoration: none;
}

ul.options {
  list-style: none;
  display: flex;
  gap: 1em;
}

ul.options li {
  color: #575B5D;
  font-size: 1.2em;
}

ul.options li:hover {
  cursor: pointer;
  font-weight: bold;
}

.navbar a {
  text-decoration: none;
  color: #575B5D;
}

/* Hamburger menu */
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: space-between;
  width: 25px;
  height: 20px;
  cursor: pointer;
}

.hamburger span {
  display: block;
  height: 3px;
  width: 100%;
  background: #575B5D;
  border-radius: 2px;
  transition: 0.3s;
}

/* Hamburger open animation */
.hamburger span.open:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}
.hamburger span.open:nth-child(2) {
  opacity: 0;
}
.hamburger span.open:nth-child(3) {
  transform: rotate(-45deg) translate(7px, -7px);
}

/* Responsive styles */
@media screen and (max-width: 768px) {
  .hamburger {
    display: flex;
  }

  ul.options {
    position: absolute;
    top: 100%;
    left: 0;
    flex-direction: column;
    background-color: #f3f3f3;
    width: 100vw;
    transform: translateY(-20px);
    opacity: 0;
    pointer-events: none;
    transition: 0.3s ease;
    padding: 0.5em 0;
    border-radius: 0 0 0 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  }

  ul.options.open {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
  }

  ul.options li {
    margin: 0;
    padding: 0.75em 0;
    border-bottom: 1px solid #000;
    box-sizing: border-box;
    display: flex;  
    align-item: center;
    text-align: center;
    justify-content: center;
  }

  ul.options li:last-child {
    padding: 0.5em 0;
    border-top: none;
    border-bottom: none;
  }
}
</style>
