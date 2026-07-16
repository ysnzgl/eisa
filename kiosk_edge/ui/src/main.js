import './app.css';
import App from './App.svelte';
import { mount } from 'svelte';
import { installGlobalHandlers } from './lib/logger.js';

installGlobalHandlers();

const app = mount(App, { target: document.getElementById('app') });
export default app;
