// Adds Firebase (Android push) only when google-services.json exists. The file is NOT in the repository (it is
// public): the APK workflow writes it from the GOOGLE_SERVICES_JSON Actions secret. Without it the app builds and
// runs with push switched off (docs/push-notifications.md).
const { existsSync } = require('node:fs');
const { join } = require('node:path');

module.exports = ({ config }) => {
  if (!existsSync(join(__dirname, 'google-services.json'))) return config;
  return { ...config, android: { ...config.android, googleServicesFile: './google-services.json' } };
};
