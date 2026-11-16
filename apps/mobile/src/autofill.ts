import { Platform, type TextInputProps } from 'react-native';

/**
 * The phone's own password manager (iOS Keychain / Google Password Manager) offers the saved login on these
 * fields and unlocks it with Face ID or a fingerprint (owner, 2026-11-16: no in-app biometric lock, but Face ID
 * at sign-in is welcome). Native code is not ours: only the hints below. The web build gets the HTML values.
 * Whether the native prompt appears can only be confirmed on a device.
 */
const web = Platform.OS === 'web';
const RULES = 'minlength: 8; maxlength: 128;'; // the server's rule: 8–128 characters

export const AUTOFILL: Record<'username' | 'currentPassword' | 'newPassword', TextInputProps> = {
  username: {
    textContentType: 'username',
    autoComplete: 'username',
    importantForAutofill: 'yes',
    autoCapitalize: 'none',
    autoCorrect: false,
  },
  currentPassword: {
    textContentType: 'password',
    autoComplete: web ? 'current-password' : 'password',
    importantForAutofill: 'yes',
    autoCapitalize: 'none',
    autoCorrect: false,
  },
  newPassword: {
    textContentType: 'newPassword',
    autoComplete: web ? 'new-password' : 'password-new',
    importantForAutofill: 'yes',
    autoCapitalize: 'none',
    autoCorrect: false,
    ...(Platform.OS === 'ios' ? { passwordRules: RULES } : {}),
  },
};
