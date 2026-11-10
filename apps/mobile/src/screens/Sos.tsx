import { useState } from 'react';
import { Linking, Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useAuth } from '../auth';
import { serviceLabel, t } from '../shared';
import { useTheme } from '../theme';
import { Banner, Button, ErrorText, H2, P, Row, Sheet } from '../ui';
import { useResource } from '../useResource';

/**
 * SOS = a dialog of choices, never an automatic action. 112 and trusted contacts are reached through the
 * phone's own dialer/SMS app; the moderator signal is recorded for manual review and is never presented as
 * "help was sent". Location sharing is not in the mobile app yet.
 */
export function SosButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button kind="danger" small label={t('sos.button')} accessibilityLabel={t('sos.buttonAria')} onPress={() => setOpen(true)} />
      {open && <SosSheet onClose={() => setOpen(false)} />}
    </>
  );
}

function SosSheet({ onClose }: { onClose: () => void }) {
  const { user } = useAuth();
  return (
    <Sheet open title={t('sos.title')} onClose={onClose}>
      <P>{t('sos.intro')}</P>
      <Button kind="danger" label={t('help.emergency.call')} onPress={() => void Linking.openURL('tel:112')} />
      {user ? (
        <>
          <TrustedContacts />
          <ModeratorSignal />
        </>
      ) : (
        <P muted>{t('sos.loginForMore')}</P>
      )}
      <Button kind="ghost" label={t('sos.close')} onPress={onClose} />
    </Sheet>
  );
}

function TrustedContacts() {
  const { palette } = useTheme();
  const res = useResource(() => api.get<Schemas['ContactRead'][]>('/safety/trusted-contacts'), []);
  const body = encodeURIComponent(t('sos.smsBody'));
  return (
    <View style={{ gap: 8 }}>
      <H2>{t('help.contacts.title')}</H2>
      {res.data && res.data.length === 0 && <P muted>{t('sos.noContacts')}</P>}
      {res.data?.map((c) => (
        <View key={c.id} style={{ gap: 6 }}>
          <Text style={{ color: palette.fg, fontWeight: '700' }}>{c.name}</Text>
          <Row>
            <Button small label={t('sos.sms')} accessibilityLabel={t('sos.smsAria', { name: c.name })} onPress={() => void Linking.openURL(`sms:${c.phone_number}?&body=${body}`)} />
            <Button small kind="ghost" label={t('sos.callContact')} accessibilityLabel={t('sos.callAria', { name: c.name })} onPress={() => void Linking.openURL(`tel:${c.phone_number}`)} />
          </Row>
        </View>
      ))}
      <P muted>{t('sos.deviceNote')}</P>
    </View>
  );
}

function ModeratorSignal() {
  const res = useResource(() => api.get<Schemas['BookingResponse'][]>('/bookings', { query: { limit: 50 } }), []);
  const [sent, setSent] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const active = (res.data ?? []).filter((b) => b.status === 'active');
  const send = async (id: string) => {
    setBusy(true);
    setErr(undefined);
    try {
      await api.post(`/safety/bookings/${id}/sos`, undefined, { query: { confirmed: true } });
      setSent(id);
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <View style={{ gap: 8 }}>
      <H2>{t('sos.moderator')}</H2>
      <P muted>{t('sos.moderatorHint')}</P>
      {res.data && active.length === 0 && <P muted>{t('sos.noActive')}</P>}
      {active.map((b) =>
        sent === b.id ? (
          <Banner key={b.id} text={t('sos.signalSent')} />
        ) : (
          <Button key={b.id} kind="danger" busy={busy} label={t('sos.sendSignal', { service: serviceLabel(b.service_code) })} onPress={() => void send(b.id)} />
        ),
      )}
      {err && <ErrorText text={err} />}
    </View>
  );
}
