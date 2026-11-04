import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { Image, ScrollView, Text, View } from 'react-native';
import { api, type Page } from '../api';
import { useAuth } from '../auth';
import { newIdempotencyKey } from '../confirm';
import { CATEGORY_NAMES, dayKey, formatDateTime, formatDay, formatMoney, STATUS_NAMES, tashkentInstant } from '../format';
import { useNav } from '../nav';
import type { GiftOrder, Payment, ProductCard, ProductPage } from '../types';
import { Badge, Body, Button, Card, Chip, Chips, Empty, ErrorText, Field, H2, Loading, Muted, Row, Screen, colors, useAction, useAsync } from '../ui';
import { ProductTile } from './Discover';

interface Cart {
  items: { product: ProductCard; quantity: number; note: string; line_total_minor: number }[];
  currency: string | null;
  subtotal_minor: number;
}

export function GiftsScreen() {
  const nav = useNav();
  const [category, setCategory] = useState('');
  const { data, error, loading } = useAsync(
    () => api.get<{ items: ProductCard[]; total: number }>('/gifts/products', { category, limit: 50 }), [category],
  );
  return (
    <Screen title="Gullar va sovg'alar" back={false}
      right={<Row><Button small variant="secondary" title="Buyurtmalar" onPress={() => nav.push('giftOrders')} /><Button small title="🛒" onPress={() => nav.push('cart')} /></Row>}>
      <Chips value={category} onChange={setCategory} options={Object.entries(CATEGORY_NAMES)} />
      <ErrorText error={error} />
      <Loading show={loading && !data} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
        {data?.items.map((item) => <ProductTile key={item.id} item={item} />)}
      </View>
      {data && !data.items.length && <Empty text="Mahsulotlar topilmadi." />}
    </Screen>
  );
}

export function ProductScreen() {
  const nav = useNav();
  const { productId } = nav.params<{ productId: string }>();
  const { data, error, reload } = useAsync(() => api.get<ProductPage>(`/gifts/products/${productId}`), [productId]);
  const [quantity, setQuantity] = useState(1);
  const [note, setNote] = useState('');
  const action = useAction();
  if (!data) return <Screen title="Mahsulot"><ErrorText error={error} /><Loading show={!error} /></Screen>;
  return (
    <Screen title={data.name} right={<Button small variant="secondary" title={data.is_favorite ? '♥' : '♡'}
      onPress={() => void action.run(() => (data.is_favorite ? api.del(`/favorites/products/${productId}`) : api.put(`/favorites/products/${productId}`)), reload)} />}>
      <ScrollView horizontal contentContainerStyle={{ gap: 8 }}>
        {data.images.map((image) => image.url && <Image key={image.id} source={{ uri: image.url }} style={{ width: 280, height: 280, borderRadius: 14, backgroundColor: colors.border }} />)}
      </ScrollView>
      <Card>
        <Text style={{ fontSize: 20, fontWeight: '800' }}>{data.name}</Text>
        <Text style={{ fontSize: 18, fontWeight: '700' }}>{formatMoney(data.price_minor, data.currency)}</Text>
        <Muted>{data.vendor_name} · {data.vendor_city}</Muted>
        <Muted>Yetkazish: ~{data.delivery_time_minutes} daq · {formatMoney(data.delivery_fee_minor, data.currency)}</Muted>
        {data.rating_average !== null && <Text>★ {data.rating_average} ({data.rating_count})</Text>}
        {data.description ? <Body>{data.description}</Body> : null}
        <Muted>Qoldiq: {data.stock}</Muted>
      </Card>
      <Row>
        <Button small variant="secondary" title="−" onPress={() => setQuantity(Math.max(1, quantity - 1))} />
        <Text style={{ fontSize: 18, fontWeight: '700' }}>{quantity}</Text>
        <Button small variant="secondary" title="+" onPress={() => setQuantity(Math.min(data.stock, quantity + 1))} />
      </Row>
      <Field label="Izoh (masalan, otkritka matni)" value={note} onChangeText={setNote} />
      <ErrorText error={action.error} />
      <Button title="Savatga qo'shish" disabled={action.busy || !data.in_stock}
        onPress={() => void action.run(() => api.put(`/gifts/cart/items/${productId}`, { quantity, note }), () => nav.push('cart'))} />
    </Screen>
  );
}

export function CartScreen() {
  const nav = useNav();
  const { data, error, loading, setData } = useAsync(() => api.get<Cart>('/gifts/cart'), []);
  const action = useAction();
  return (
    <Screen title="Savat">
      <ErrorText error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data?.items.map((line) => (
        <Card key={line.product.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700', flexShrink: 1 }}>{line.product.name} × {line.quantity}</Text>
            <Text>{formatMoney(line.line_total_minor, line.product.currency)}</Text>
          </Row>
          {line.note ? <Muted>{line.note}</Muted> : null}
          <Button small variant="secondary" title="Olib tashlash"
            onPress={() => void action.run(async () => setData(await api.del<Cart>(`/gifts/cart/items/${line.product.id}`)))} />
        </Card>
      ))}
      {data && !data.items.length && <Empty text="Savat bo'sh." />}
      {data && data.items.length > 0 && (
        <>
          <Row style={{ justifyContent: 'space-between' }}><H2>Jami (yetkazishsiz)</H2><H2>{formatMoney(data.subtotal_minor, data.currency ?? 'UZS')}</H2></Row>
          <Button title="Rasmiylashtirish" onPress={() => nav.push('giftCheckout')} />
        </>
      )}
    </Screen>
  );
}

const TIMES = ['10:00', '12:00', '14:00', '16:00', '18:00', '20:00'];

export function GiftCheckoutScreen() {
  const nav = useNav();
  const { me } = useAuth();
  const days = Array.from({ length: 7 }, (_, i) => dayKey(new Date(Date.now() + i * 86_400_000)));
  const [recipient, setRecipient] = useState(me?.display_name ?? '');
  const [phone, setPhone] = useState(me?.phone_number ?? '');
  const [address, setAddress] = useState('');
  const [day, setDay] = useState(days[1]);
  const [time, setTime] = useState('14:00');
  const [note, setNote] = useState('');
  const action = useAction();
  const submit = () => void action.run(async () => {
    const payment = await api.post<Payment>('/payments/gifts/checkout', {
      idempotency_key: newIdempotencyKey('gift'),
      delivery: { recipient_name: recipient, recipient_phone: phone, address, delivery_at: tashkentInstant(day, time), note },
    });
    if (payment.checkout_url) await WebBrowser.openBrowserAsync(payment.checkout_url);
    nav.replace('giftOrders');
  });
  return (
    <Screen title="Yetkazish">
      <Field label="Qabul qiluvchi" value={recipient} onChangeText={setRecipient} />
      <Field label="Qabul qiluvchi telefoni" value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
      <Field label="Manzil" value={address} onChangeText={setAddress} multiline />
      <H2>Sana</H2>
      <Chips value={day} onChange={(v) => setDay(v || days[1])} options={days.map((d) => [d, formatDay(`${d}T12:00:00+05:00`)])} />
      <H2>Vaqt</H2>
      <Row>{TIMES.map((t) => <Chip key={t} label={t} selected={time === t} onPress={() => setTime(t)} />)}</Row>
      <Field label="Izoh" value={note} onChangeText={setNote} />
      <ErrorText error={action.error} />
      <Button title="To'lovga o'tish" disabled={action.busy || !recipient || !phone || !address} onPress={submit} />
    </Screen>
  );
}

export function GiftOrdersScreen() {
  const { data, error, loading, reload } = useAsync(() => api.get<Page<GiftOrder>>('/gifts/orders', { limit: 50 }), []);
  const action = useAction();
  return (
    <Screen title="Buyurtmalarim">
      <ErrorText error={error ?? action.error} />
      <Loading show={loading && !data} />
      {data?.items.map((order) => (
        <Card key={order.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Text style={{ fontWeight: '700' }}>{order.vendor_name}</Text>
            <Badge label={STATUS_NAMES[order.status] ?? order.status} tone={order.status === 'cancelled' ? 'danger' : order.status === 'delivered' ? 'green' : 'amber'} />
          </Row>
          <Muted>{order.items.map((i) => `${i.product_name} ×${i.quantity}`).join(', ')}</Muted>
          <Muted>{formatDateTime(order.delivery_at)} · {order.delivery_address}</Muted>
          <Text style={{ fontWeight: '600' }}>{formatMoney(order.total_minor, order.currency)}</Text>
          {order.status === 'new' && !order.booking_id && (
            <Button small variant="danger" title="Bekor qilish" onPress={() => void action.run(() => api.post(`/gifts/orders/${order.id}/cancel`), reload)} />
          )}
          {order.status === 'delivered' && (
            <Button small variant="secondary" title="★★★★★ baholash" onPress={() => void action.run(() => api.post(`/gifts/orders/${order.id}/review`, { rating: 5 }), reload)} />
          )}
        </Card>
      ))}
      {data && !data.items.length && <Empty text="Buyurtmalar yo'q." />}
    </Screen>
  );
}
