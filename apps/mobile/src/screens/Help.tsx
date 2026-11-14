import { useState, type ReactNode } from 'react';
import { Linking, Pressable, Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { useAuth } from '../auth';
import { ICONS, Icon } from '../brand';
import { useNav } from '../nav';
import { REPORT_CATEGORY, REPORT_STATUS, SUPPORT_STATUS, t, type Key } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, Chip, ChipGroup, ErrorText, Field, H1, H2, Loading, P, Row, Screen, Tag } from '../ui';
import { useResource } from '../useResource';
import { SosButton } from './Sos';

type Report = Schemas['ReportRead'];
type Contact = Schemas['ContactRead'];
type SupportCategory = Schemas['SupportWrite']['category'];
type Ticket = Schemas['SupportRead'];

// The same lists as apps/web/src/pages/Help.tsx (texts come from the shared dictionaries; nothing new is invented).
const FAQ = ['what', 'book', 'pay', 'cancel', 'verified', 'companion', 'privacy', 'data', 'delete'] as const;
const SUPPORT_CATEGORIES: SupportCategory[] = ['account', 'booking', 'payment', 'safety', 'technical', 'other'];
const PHONE = /^\+?[0-9]{7,15}$/;

/**
 * Help & safety, native (owner, 2026-11-14): the web's /help — emergency (112, SOS), reports go through a booking,
 * my reports, trusted contacts, FAQ, support requests. SOS never claims that help was sent (see Sos.tsx).
 */
export function HelpScreen() {
  const nav = useNav();
  const { user } = useAuth();
  return (
    <Screen>
      {nav.canGoBack && (
        <Row>
          <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
        </Row>
      )}
      <H1>{t('help.title')}</H1>
      <P muted>{t('help.lead')}</P>

      <EmergencyCard>
        <H2>{t('help.emergency.title')}</H2>
        <P>{t('help.emergency.body')}</P>
        <Row>
          <Button label={t('help.emergency.call')} onPress={() => void Linking.openURL('tel:112')} />
          <SosButton kind="ghost" />
        </Row>
      </EmergencyCard>

      <Card style={{ gap: 10 }}>
        <H2>{t('help.report.title')}</H2>
        <P>{t('help.report.body')}</P>
        <P muted style={{ fontSize: 14 }}>{t('help.report.noBooking')}</P>
        <Row>
          {user ? (
            <Button kind="ghost" label={t('help.report.toBookings')} onPress={() => nav.switchTab('bookings')} />
          ) : (
            <Button kind="ghost" label={t('nav.login')} onPress={() => nav.switchTab('login')} />
          )}
        </Row>
      </Card>

      {user ? (
        <>
          <MyReports />
          <TrustedContacts />
        </>
      ) : (
        <Banner text={t('help.loginFor')} />
      )}

      <Faq />

      <Card style={{ gap: 10 }}>
        <H2>{t('help.contact.title')}</H2>
        <P muted>{t('help.support.body')}</P>
        {user ? (
          <SupportRequests />
        ) : (
          <Row>
            <Button kind="ghost" label={t('help.support.login')} onPress={() => nav.switchTab('login')} />
          </Row>
        )}
      </Card>
    </Screen>
  );
}

/** The web's .emergency section: the carrot border marks it (meaning is carried by the words). */
function EmergencyCard({ children }: { children: ReactNode }) {
  const { palette } = useTheme();
  return <Card style={{ gap: 10, borderColor: palette.accent, borderWidth: 1.5 }}>{children}</Card>;
}

function ListRow({ title, sub, right, first }: { title: string; sub?: string; right?: ReactNode; first?: boolean }) {
  const { palette } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderTopWidth: first ? 0 : 1, borderTopColor: palette.glassLine }}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ color: palette.fg, fontFamily: FONT.bold, fontSize: 15 }}>{title}</Text>
        {!!sub && (
          <Text numberOfLines={3} style={{ color: palette.muted, fontFamily: FONT.body, fontSize: 14 }}>
            {sub}
          </Text>
        )}
      </View>
      {right}
    </View>
  );
}

function MyReports() {
  const res = useResource(() => api.get<Report[]>('/safety/reports'), []);
  return (
    <Card style={{ gap: 6 }}>
      <H2>{t('help.myReports')}</H2>
      {res.loading && !res.data ? (
        <Loading />
      ) : res.error ? (
        <>
          <ErrorText text={errorText(res.error)} />
          <Button kind="ghost" label={t('common.retry')} onPress={res.reload} />
        </>
      ) : !res.data?.length ? (
        <P muted>{t('help.myReportsEmpty')}</P>
      ) : (
        res.data.map((r, i) => (
          <ListRow
            key={r.id}
            first={i === 0}
            title={REPORT_CATEGORY[r.category] ?? r.category}
            sub={r.description}
            right={<Tag text={REPORT_STATUS[r.status]?.label ?? r.status} attention={REPORT_STATUS[r.status]?.tone === 'warn'} />}
          />
        ))
      )}
    </Card>
  );
}

function TrustedContacts() {
  const res = useResource(() => api.get<Contact[]>('/safety/trusted-contacts'), []);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string>();
  const cleanPhone = phone.replace(/[\s()-]/g, '');
  const nameErr = touched && !name.trim() ? t('help.contacts.nameRequired') : undefined;
  const phoneErr = touched && !PHONE.test(cleanPhone) ? t('help.contacts.phoneInvalid') : undefined;
  const add = async () => {
    setTouched(true);
    if (!name.trim() || !PHONE.test(cleanPhone)) return;
    setBusy(true);
    setNotice(undefined);
    try {
      await api.post<Contact>('/safety/trusted-contacts', { name: name.trim(), phone_number: cleanPhone });
      setNotice(t('help.contacts.added'));
      setName('');
      setPhone('');
      setTouched(false);
      res.reload();
    } catch (e) {
      setNotice(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (c: Contact) => {
    setNotice(undefined);
    try {
      await api.del(`/safety/trusted-contacts/${c.id}`);
      setNotice(t('help.contacts.removed'));
      res.reload();
    } catch (e) {
      setNotice(errorText(e));
    }
  };
  return (
    <Card style={{ gap: 10 }}>
      <H2>{t('help.contacts.title')}</H2>
      <P muted>{t('help.contacts.body')}</P>
      {notice && <Banner text={notice} />}
      {res.loading && !res.data ? (
        <Loading />
      ) : res.error ? (
        <ErrorText text={errorText(res.error)} />
      ) : !res.data?.length ? (
        <P muted style={{ fontSize: 14 }}>{t('help.contacts.empty')}</P>
      ) : (
        <View>
          {res.data.map((c, i) => (
            <ListRow
              key={c.id}
              first={i === 0}
              title={c.name}
              sub={c.phone_number}
              right={
                <Button
                  small
                  kind="ghost"
                  label={t('help.contacts.removeShort')}
                  accessibilityLabel={t('help.contacts.remove', { name: c.name })}
                  onPress={() => void remove(c)}
                />
              }
            />
          ))}
        </View>
      )}
      <Field label={t('help.contacts.name')} value={name} maxLength={128} autoComplete="off" onChangeText={setName} error={nameErr} />
      <Field
        label={t('help.contacts.phone')}
        keyboardType="phone-pad"
        value={phone}
        onChangeText={setPhone}
        hint={t('help.contacts.phoneHint')}
        error={phoneErr}
      />
      <Row>
        <Button label={t('help.contacts.add')} busy={busy} onPress={() => void add()} />
      </Row>
    </Card>
  );
}

/** FAQ as an accordion (the web uses <details>): one question open at a time. */
function Faq() {
  const { palette } = useTheme();
  const [open, setOpen] = useState<string>();
  return (
    <Card style={{ gap: 0 }}>
      <H2>{t('help.faq.title')}</H2>
      {FAQ.map((id, i) => {
        const on = open === id;
        return (
          <View key={id} style={{ borderTopWidth: i ? 1 : 0, borderTopColor: palette.glassLine }}>
            <Pressable
              role="button"
              aria-expanded={on}
              onPress={() => setOpen(on ? undefined : id)}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 48, paddingVertical: 10 }}
            >
              <Text style={{ flex: 1, color: palette.fg, fontFamily: FONT.medium, fontSize: 15 }}>{t(`help.faq.${id}.q` as Key)}</Text>
              <View style={{ transform: [{ rotate: on ? '90deg' : '0deg' }] }}>
                <Icon d={ICONS.chevron} size={18} color={palette.muted} />
              </View>
            </Pressable>
            {on && <P style={{ paddingBottom: 12 }}>{t(`help.faq.${id}.a` as Key)}</P>}
          </View>
        );
      })}
    </Card>
  );
}

function SupportRequests() {
  const res = useResource(() => api.get<Ticket[]>('/support/requests'), []);
  const [category, setCategory] = useState<SupportCategory>('account');
  const [message, setMessage] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string>();
  const short = message.trim().length < 10;
  const send = async () => {
    setTouched(true);
    if (short) return;
    setBusy(true);
    setNotice(undefined);
    try {
      await api.post<Ticket>('/support/requests', { category, message: message.trim() });
      setNotice(t('help.support.sent'));
      setMessage('');
      setTouched(false);
      res.reload();
    } catch (e) {
      setNotice(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      {notice && <Banner text={notice} />}
      <P style={{ fontFamily: FONT.medium, fontSize: 15 }}>{t('help.support.category')}</P>
      <ChipGroup label={t('help.support.category')}>
        {SUPPORT_CATEGORIES.map((c) => (
          <Chip key={c} label={t(`help.support.cat.${c}` as Key)} selected={category === c} onPress={() => setCategory(c)} />
        ))}
      </ChipGroup>
      <Field
        label={t('help.support.message')}
        value={message}
        onChangeText={setMessage}
        multiline
        numberOfLines={4}
        maxLength={4000}
        error={touched && short ? t('help.feedback.min') : undefined}
      />
      <Row>
        <Button label={t('help.support.send')} busy={busy} onPress={() => void send()} />
      </Row>
      {!!res.data?.length && (
        <View style={{ gap: 4 }}>
          <P style={{ fontFamily: FONT.bold }}>{t('help.support.mine')}</P>
          {res.data.map((r, i) => (
            <View key={r.id}>
              <ListRow
                first={i === 0}
                title={t(`help.support.cat.${r.category}` as Key)}
                sub={r.message}
                right={<Tag text={SUPPORT_STATUS[r.status]?.label ?? r.status} attention={SUPPORT_STATUS[r.status]?.tone === 'warn'} />}
              />
              {r.reply && <Banner text={`${t('help.support.reply')}: ${r.reply}`} />}
            </View>
          ))}
        </View>
      )}
    </>
  );
}
