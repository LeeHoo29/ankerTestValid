<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// 根组件，所有路由组件都会在这里渲染
</script>

<style>
#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
}
</style> 