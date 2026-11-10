// The app shares the web client's i18n dictionaries and pure helpers (apps/web/src) instead of copying them,
// so there is one source of truth for uz/ru/en text. Those files must resolve `react` from THIS app's
// node_modules (one React instance), hence the explicit module path and no hierarchical lookup.
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);
config.watchFolders = [path.resolve(__dirname, '../web/src')];
config.resolver.nodeModulesPaths = [path.resolve(__dirname, 'node_modules')];
config.resolver.disableHierarchicalLookup = true;

module.exports = config;
