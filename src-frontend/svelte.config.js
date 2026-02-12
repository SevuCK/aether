import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      pages: 'build',  // Electron looks for this folder
      assets: 'build',
      fallback: 'index.html' // Important for Single Page Apps (SPA)
    })
  }
};