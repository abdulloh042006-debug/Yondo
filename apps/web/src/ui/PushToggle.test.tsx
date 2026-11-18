import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const get = vi.hoisted(() => vi.fn());
const put = vi.hoisted(() => vi.fn());
const del = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, put, del } };
});
import { t } from '../i18n';
import { forgetPushDevice, pushState } from '../lib/push';
import { PushToggle } from './PushToggle';

const VAPID = 'BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8';

type Perm = NotificationPermission;
let permission: Perm;
let subscription: { endpoint: string; toJSON: () => unknown; unsubscribe: ReturnType<typeof vi.fn> } | null;
const requestPermission = vi.fn<() => Promise<Perm>>();
const subscribe = vi.fn();
const register = vi.fn();

function install({ ios = false, push = true } = {}) {
  const reg = {
    pushManager: {
      getSubscription: vi.fn(async () => subscription),
      subscribe,
    },
  };
  const NotificationMock = Object.assign(function Notification() {}, { requestPermission });
  Object.defineProperty(NotificationMock, 'permission', { get: () => permission, configurable: true });
  vi.stubGlobal('Notification', NotificationMock);
  if (push) vi.stubGlobal('PushManager', function PushManager() {});
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { register, ready: Promise.resolve(reg), getRegistration: vi.fn(async () => reg) },
  });
  Object.defineProperty(navigator, 'userAgent', {
    configurable: true,
    value: ios ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari' : 'Mozilla/5.0 (X11; Linux) Chrome',
  });
}

beforeEach(() => {
  permission = 'default';
  subscription = null;
  localStorage.removeItem('yondo.push.device');
  get.mockResolvedValue({ web: { enabled: true, vapid_public_key: VAPID }, android: { enabled: false } });
  put.mockResolvedValue({ id: 'dev-1' });
  del.mockResolvedValue(undefined);
  requestPermission.mockImplementation(async () => {
    permission = 'granted';
    return 'granted';
  });
  subscribe.mockImplementation(async () => {
    subscription = {
      endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
      toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/abc', keys: { p256dh: 'P'.repeat(87), auth: 'A'.repeat(22) } }),
      unsubscribe: vi.fn(async () => true),
    };
    return subscription;
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const toggle = () => screen.getByRole('switch', { name: new RegExp(t('push.title')) });

describe('Settings → Push bildirişnomalar (Web Push)', () => {
  it('never asks for permission on load; a tap asks, subscribes with the VAPID key and registers the device', async () => {
    install();
    render(<PushToggle />);
    await screen.findByText(t('push.state.off'));
    expect(requestPermission).not.toHaveBeenCalled();
    expect(register).not.toHaveBeenCalled();

    await userEvent.click(toggle());
    await screen.findByText(t('push.state.on'));
    expect(requestPermission).toHaveBeenCalledTimes(1);
    expect(register).toHaveBeenCalledWith('/sw.js');
    const opts = subscribe.mock.calls[0][0];
    expect(opts.userVisibleOnly).toBe(true);
    expect(opts.applicationServerKey).toBeInstanceOf(Uint8Array);
    expect(opts.applicationServerKey.length).toBe(65);
    expect(put).toHaveBeenCalledWith('/push/devices', {
      platform: 'web',
      endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
      p256dh: 'P'.repeat(87),
      auth: 'A'.repeat(22),
    });
    expect(toggle()).toBeChecked();
    expect(localStorage.getItem('yondo.push.device')).toBe('dev-1');
  });

  it('turning it off unsubscribes the browser and unregisters the device', async () => {
    install();
    render(<PushToggle />);
    await screen.findByText(t('push.state.off'));
    await userEvent.click(toggle());
    await screen.findByText(t('push.state.on'));
    const sub = subscription!;
    await userEvent.click(toggle());
    await screen.findByText(t('push.state.off'));
    expect(sub.unsubscribe).toHaveBeenCalled();
    expect(del).toHaveBeenCalledWith('/push/devices/dev-1');
    expect(localStorage.getItem('yondo.push.device')).toBeNull();
  });

  it('a refusal shows how to re-enable it in the browser and disables the switch', async () => {
    install();
    requestPermission.mockImplementation(async () => {
      permission = 'denied';
      return 'denied';
    });
    render(<PushToggle />);
    await screen.findByText(t('push.state.off'));
    await userEvent.click(toggle());
    await screen.findByText(t('push.state.denied'));
    expect(toggle()).toBeDisabled();
    expect(put).not.toHaveBeenCalled();
  });

  it('already denied on load: explained, no prompt', async () => {
    install();
    permission = 'denied';
    render(<PushToggle />);
    await screen.findByText(t('push.state.denied'));
    expect(requestPermission).not.toHaveBeenCalled();
  });

  it('a browser without Push API is told so; the switch is disabled', async () => {
    install({ push: false });
    render(<PushToggle />);
    await screen.findByText(t('push.state.unsupported'));
    expect(toggle()).toBeDisabled();
  });

  it('iPhone Safari in a tab: explains "Add to Home Screen" first', async () => {
    install({ ios: true });
    render(<PushToggle />);
    await screen.findByText(t('push.state.iosInstall'));
    expect(toggle()).toBeDisabled();
  });

  it('server without Web Push: unavailable, nothing subscribed', async () => {
    install();
    get.mockResolvedValue({ web: { enabled: false, vapid_public_key: null }, android: { enabled: false } });
    render(<PushToggle />);
    await screen.findByText(t('push.state.off'));
    await userEvent.click(toggle());
    await screen.findByText(t('push.state.unavailable'));
    expect(subscribe).not.toHaveBeenCalled();
  });

  it('a failed registration shows an error and leaves the switch off', async () => {
    install();
    put.mockRejectedValue(new Error('network'));
    render(<PushToggle />);
    await screen.findByText(t('push.state.off'));
    await userEvent.click(toggle());
    expect(await screen.findByRole('alert')).toHaveTextContent(t('push.error'));
    expect(toggle()).not.toBeChecked();
  });

  it('sign-out forgets this browser’s device; without one it does nothing', async () => {
    install();
    await forgetPushDevice();
    expect(del).not.toHaveBeenCalled();
    permission = 'granted';
    localStorage.setItem('yondo.push.device', 'dev-9');
    await subscribe();
    expect(await pushState()).toBe('on');
    await forgetPushDevice();
    expect(del).toHaveBeenCalledWith('/push/devices/dev-9');
    await waitFor(() => expect(localStorage.getItem('yondo.push.device')).toBeNull());
  });
});
