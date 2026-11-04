import * as ImagePicker from 'expo-image-picker';
import { useEffect, useRef, useState } from 'react';
import { FlatList, Image, KeyboardAvoidingView, Platform, Text, TextInput, View } from 'react-native';
import { api, realtimeUrl } from '../api';
import { useAuth } from '../auth';
import { formatDateTime, formatTime, STATUS_NAMES } from '../format';
import { useNav } from '../nav';
import type { Conversation, Message } from '../types';
import { Badge, Button, Card, Empty, ErrorText, Loading, Muted, Row, Screen, colors, styles, useAction, useAsync } from '../ui';

export function ConversationsScreen() {
  const nav = useNav();
  const { data, error, loading } = useAsync(() => api.get<Conversation[]>('/chat/conversations'), []);
  return (
    <Screen title="Chat" back={false}>
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      {data?.map((item) => (
        <Card key={item.booking_id} onPress={() => nav.push('chat', { bookingId: item.booking_id })}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700' }}>{item.counterpart_name ?? 'Suhbat'}</Text>
            {item.unread > 0 && <Badge label={String(item.unread)} />}
          </Row>
          <Muted>{STATUS_NAMES[item.booking_status] ?? item.booking_status} · {formatDateTime(item.starts_at)}</Muted>
          {item.last_message && <Text numberOfLines={1}>{item.last_message.body || (item.last_message.kind === 'image' ? '📷 Rasm' : '📍 Joy')}</Text>}
        </Card>
      ))}
      {data && !data.length && <Empty text="Suhbatlar bron qilingandan keyin paydo bo'ladi." />}
    </Screen>
  );
}

export function ChatScreen() {
  const nav = useNav();
  const { me } = useAuth();
  const { bookingId } = nav.params<{ bookingId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const action = useAction();
  const listRef = useRef<FlatList<Message>>(null);

  const merge = (incoming: Message[]) =>
    setMessages((current) => {
      const byId = new Map(current.map((m) => [m.id, m]));
      for (const message of incoming) byId.set(message.id, { ...byId.get(message.id), ...message });
      return [...byId.values()].sort((a, b) => a.created_at.localeCompare(b.created_at));
    });

  useEffect(() => {
    let socket: WebSocket | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;
    const load = async () => {
      try {
        merge(await api.get<Message[]>(`/chat/bookings/${bookingId}/messages`, { limit: 100 }));
        await api.post(`/chat/bookings/${bookingId}/read`);
      } catch (exc) {
        action.setError(String(exc));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const url = realtimeUrl();
    if (url) {
      socket = new WebSocket(url);
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(String(event.data));
          if (data.type === 'chat_message' && data.message.booking_id === bookingId) {
            // Realtime payloads omit signed image URLs; refetch to get them.
            if (data.message.kind === 'image') void load();
            else merge([{ image_url: null, ...data.message }]);
          }
        } catch {
          // Ignore heartbeat/non-JSON frames.
        }
      };
      socket.onerror = () => {
        // Fall back to polling when the realtime socket is unavailable.
        poll ??= setInterval(() => void load(), 5000);
      };
    } else {
      poll = setInterval(() => void load(), 5000);
    }
    return () => {
      cancelled = true;
      socket?.close();
      if (poll) clearInterval(poll);
    };
  }, [bookingId]); // eslint-disable-line react-hooks/exhaustive-deps

  const send = () => {
    const body = text.trim();
    if (!body) return;
    void action.run(async () => {
      merge([await api.post<Message>(`/chat/bookings/${bookingId}/messages`, { kind: 'text', body })]);
      setText('');
    });
  };
  const sendImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 });
    if (result.canceled) return;
    const asset = result.assets[0];
    await action.run(async () => merge([await api.uploadImage<Message>(`/chat/bookings/${bookingId}/images`, asset.uri, asset.mimeType)]));
  };

  return (
    <Screen title="Chat" scroll={false}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Loading show={loading} />
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          contentContainerStyle={{ gap: 8, paddingBottom: 8 }}
          renderItem={({ item }) => <Bubble message={item} mine={item.sender_id === me?.id} />}
        />
        <ErrorText error={action.error} />
        <Muted>Telefon raqam va shaxsiy kontaktlarni almashmang — muloqot va to'lov faqat Yondo ichida.</Muted>
        <Row style={{ flexWrap: 'nowrap', marginTop: 6 }}>
          <Button small variant="secondary" title="📷" onPress={() => void sendImage()} disabled={action.busy} />
          <TextInput style={[styles.input, { flex: 1 }]} value={text} onChangeText={setText} placeholder="Xabar…" onSubmitEditing={send} returnKeyType="send" />
          <Button small title="Yuborish" onPress={send} disabled={action.busy || !text.trim()} />
        </Row>
      </KeyboardAvoidingView>
    </Screen>
  );
}

function Bubble({ message, mine }: { message: Message; mine: boolean }) {
  if (message.kind === 'system' || message.kind === 'booking_details') {
    return <Text style={{ alignSelf: 'center', color: colors.muted, fontSize: 12, textAlign: 'center' }}>{message.body}</Text>;
  }
  const place = message.kind === 'meeting_point' ? (message.payload as { name?: string; address?: string }) : null;
  return (
    <View style={{ alignSelf: mine ? 'flex-end' : 'flex-start', maxWidth: '80%', backgroundColor: mine ? colors.primary : colors.surface, borderRadius: 14, padding: 10, borderWidth: mine ? 0 : 1, borderColor: colors.border }}>
      {message.image_url && <Image source={{ uri: message.image_url }} style={{ width: 200, height: 200, borderRadius: 10 }} />}
      {place && <Text style={{ color: mine ? '#fff' : colors.text, fontWeight: '700' }}>📍 {place.name} {place.address ?? ''}</Text>}
      {message.body ? <Text style={{ color: mine ? '#fff' : colors.text }}>{message.body}</Text> : null}
      <Text style={{ color: mine ? '#E0DCFF' : colors.muted, fontSize: 11, alignSelf: 'flex-end' }}>{formatTime(message.created_at)}</Text>
    </View>
  );
}

export { Empty };
