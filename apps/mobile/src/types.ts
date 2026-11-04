// API response shapes used by the app (subset of the OpenAPI schema).

export interface Me {
  id: string;
  phone_number: string;
  display_name: string | null;
  age: number | null;
  gender: string | null;
  city: string | null;
  roles: string[];
  account_status: string | null;
  profile_complete: boolean;
}

export interface PhotoView {
  id: string;
  url: string | null;
  width: number;
  height: number;
  caption: string;
}

export interface CompanionStats {
  rating_average: number | null;
  rating_count: number;
  completed_bookings: number;
}

export interface CompanionCard {
  profile_id: string;
  display_name: string;
  age: number | null;
  gender: string | null;
  city: string | null;
  area: string | null;
  primary_photo: PhotoView | null;
  services: string[];
  min_price_minor: number | null;
  currency: string | null;
  distance_km: number | null;
  is_favorite: boolean;
  badges: string[];
  stats: CompanionStats;
}

export interface ServiceSummary {
  id: string;
  service_code: string;
  description: string;
  price_minor: number;
  currency: string;
  unit_minutes: number;
}

export interface Slot {
  starts_at: string;
  ends_at: string;
  timezone: string;
}

export interface PublicProfile extends CompanionCard {
  user_id: string;
  bio: string;
  languages: string[];
  interests: string[];
  photos: PhotoView[];
  service_details: ServiceSummary[];
  availability: Slot[];
  member_since: string;
}

export interface ProductCard {
  id: string;
  category: string;
  name: string;
  price_minor: number;
  currency: string;
  vendor_id: string;
  vendor_name: string;
  image: { id: string; url: string | null } | null;
  rating_average: number | null;
  rating_count: number;
  delivery_time_minutes: number;
  in_stock: boolean;
  is_favorite: boolean;
}

export interface ProductPage extends ProductCard {
  description: string;
  images: { id: string; url: string | null }[];
  stock: number;
  vendor_city: string;
  delivery_fee_minor: number;
}

export interface Home {
  sections: { key: string; title: string; items: CompanionCard[] }[];
  popular_experiences: { service_code: string; companions: number }[];
  gift_sections: { key: string; title: string; items: ProductCard[] }[];
}

export interface MeetingPlace {
  name: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
}

export interface Party {
  id: string;
  display_name: string | null;
  age: number | null;
  gender: string | null;
  rating_average: number | null;
  rating_count: number;
}

export interface Booking {
  id: string;
  status: string;
  role: 'customer' | 'companion' | 'admin';
  customer: Party;
  companion: Party;
  profile_id: string;
  service_id: string | null;
  service_code: string;
  currency: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  timezone: string;
  meeting_place: MeetingPlace;
  note: string;
  service_amount_minor: number;
  platform_fee_minor: number;
  total_minor: number;
  companion_payout_minor: number | null;
  refund_minor: number;
  contract: Record<string, unknown>;
  payment_due_at: string | null;
  request_expires_at: string;
  cancellation_reason: string | null;
  customer_checked_in_at: string | null;
  companion_checked_in_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  actions: string[];
}

export interface Quote {
  service_amount_minor: number;
  platform_fee_minor: number;
  total_minor: number;
  currency: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  contract: { cancellation_policy: { free_cancellation_hours: number; late_cancellation_refund_bps: number }; platform_rules: string[] };
}

export interface Payment {
  id: string;
  status: string;
  amount_minor: number;
  currency: string;
  checkout_url: string | null;
  booking_id: string | null;
}

export interface Message {
  id: string;
  booking_id: string;
  sender_id: string | null;
  kind: string;
  body: string;
  payload: Record<string, unknown>;
  image_url: string | null;
  created_at: string;
}

export interface Conversation {
  booking_id: string;
  booking_status: string;
  counterpart_name: string | null;
  starts_at: string;
  last_message: Message | null;
  unread: number;
  can_send: boolean;
}

export interface Notification {
  id: string;
  kind: string;
  title: string;
  body: string;
  data: Record<string, string>;
  read_at: string | null;
  created_at: string;
}

export interface GiftOrder {
  id: string;
  vendor_name: string | null;
  booking_id: string | null;
  status: string;
  recipient_name: string;
  delivery_address: string;
  delivery_at: string;
  currency: string;
  total_minor: number;
  items: { product_name: string; quantity: number }[];
}

export interface Contact {
  id: string;
  name: string;
  phone_number: string;
  relationship: string;
}
