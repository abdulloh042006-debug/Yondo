# API overview

Generated from the OpenAPI schema (`/docs` in development). All paths below use the
`/api/v1` prefix unless they start with `/health`. Authentication: `Authorization: Bearer
<access token>` from phone OTP. Errors use one shape: `{code, message, request_id, errors?}`.
Money is always integer minor units with a three-letter currency; timestamps are UTC ISO 8601.

Total operations: 171.

## admin: analytics

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/admin/analytics` | Metrics |

## admin: bookings & payments

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/admin/bookings` | Booking List |
| GET | `/admin/bookings/{booking_id}` | Booking Detail |
| POST | `/admin/bookings/{booking_id}/cancel` | Cancel Booking |
| GET | `/admin/payments` | Payment List |
| GET | `/admin/payouts` | Payout List |
| POST | `/admin/payouts/{payout_id}/mark-paid` | Mark Paid |
| GET | `/admin/refunds` | Refund List |
| POST | `/admin/refunds/process` | Run Refunds |

## admin: gifts

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/admin/gift-orders` | Gift Orders |
| POST | `/admin/gift-orders/{order_id}/cancel` | Cancel Gift Order |
| GET | `/admin/products` | Products |
| POST | `/admin/products/{product_id}/moderation` | Moderate Product |
| GET | `/admin/vendors` | Vendors |
| POST | `/admin/vendors/{vendor_id}/decision` | Decide Vendor |

## admin: trust & safety

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/admin/audit` | Audit Log |
| GET | `/admin/companions/applications` | Application Queue |
| GET | `/admin/companions/profiles` | Content Queue |
| GET | `/admin/disputes` | Dispute List |
| GET | `/admin/disputes/{dispute_id}` | Dispute Detail |
| POST | `/admin/disputes/{dispute_id}/resolve` | Resolve |
| POST | `/admin/disputes/{dispute_id}/review` | Take Dispute |
| GET | `/admin/reports` | Reports |
| POST | `/admin/reports/{report_id}/status` | Update Report |
| GET | `/admin/reviews` | Review List |
| POST | `/admin/reviews/{review_id}/moderation` | Moderate Review |
| GET | `/admin/sos` | Sos List |
| POST | `/admin/sos/{alert_id}/status` | Update Sos |
| GET | `/admin/verifications` | Verification Queue |
| GET | `/admin/verifications/{verification_id}` | Verification Detail |
| POST | `/admin/verifications/{verification_id}/decision` | Verification Decision |

## admin: users

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/admin/users` | List Users |
| GET | `/admin/users/{user_id}` | User Detail |
| POST | `/admin/users/{user_id}/moderation` | Moderate |
| POST | `/admin/users/{user_id}/roles` | Change Role |

## authentication

| Method | Path | Summary |
| --- | --- | --- |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Get Profile |
| POST | `/auth/otp/request` | Request Otp |
| POST | `/auth/otp/verify` | Verify |
| PUT | `/auth/profile` | Update Profile |
| POST | `/auth/refresh` | Refresh |
| PUT | `/auth/roles` | Select Roles |

## bookings

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/bookings` | List Bookings |
| POST | `/bookings` | Create Booking |
| POST | `/bookings/quote` | Quote |
| GET | `/bookings/{booking_id}` | Get Booking |
| POST | `/bookings/{booking_id}/accept` | Accept Booking |
| POST | `/bookings/{booking_id}/cancel` | Cancel Booking |
| GET | `/bookings/{booking_id}/cancellation` | Cancellation Preview |
| POST | `/bookings/{booking_id}/decline` | Decline Booking |
| GET | `/bookings/{booking_id}/events` | Booking Events |
| GET | `/bookings/{booking_id}/rebook` | Rebook Template |

## chat

| Method | Path | Summary |
| --- | --- | --- |
| POST | `/chat/bookings/{booking_id}/images` | Send Image |
| GET | `/chat/bookings/{booking_id}/messages` | Messages |
| POST | `/chat/bookings/{booking_id}/messages` | Send Message |
| POST | `/chat/bookings/{booking_id}/read` | Mark Read |
| GET | `/chat/conversations` | Conversations |
| GET | `/chat/unread` | Unread Total |

## companion approval

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/companions/admin/applications/{application_id}` | Read Application |
| POST | `/companions/admin/applications/{application_id}/decision` | Decide Application |
| POST | `/companions/admin/profiles/{profile_id}/decision` | Decide Profile |
| GET | `/companions/admin/users/{user_id}/content-review` | Read Content Review |
| GET | `/companions/admin/users/{user_id}/photos` | Read Photos |
| GET | `/companions/admin/users/{user_id}/photos/{photo_id}/download` | Read Photo |
| GET | `/companions/admin/users/{user_id}/profile` | Read Profile |
| GET | `/companions/admin/users/{user_id}/services` | Read Services |

## companion photos

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/companions/me/photos` | List Photos |
| POST | `/companions/me/photos` | Upload Photo |
| PUT | `/companions/me/photos/order` | Reorder Photos |
| DELETE | `/companions/me/photos/{photo_id}` | Delete Photo |
| PATCH | `/companions/me/photos/{photo_id}` | Edit Caption |
| GET | `/companions/me/photos/{photo_id}/download` | Download Photo |

## companion resources

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/companions/me/availability` | List Availability |
| POST | `/companions/me/availability` | Create Availability |
| DELETE | `/companions/me/availability/{availability_id}` | Delete Availability |
| PUT | `/companions/me/availability/{availability_id}` | Update Availability |
| GET | `/companions/me/services` | List Services |
| POST | `/companions/me/services` | Create Service |
| DELETE | `/companions/me/services/{service_id}` | Delete Service |
| PUT | `/companions/me/services/{service_id}` | Update Service |

## companions

| Method | Path | Summary |
| --- | --- | --- |
| POST | `/companions/me/activate` | Activate |
| GET | `/companions/me/application` | Get Application |
| POST | `/companions/me/application` | Create Application |
| PUT | `/companions/me/application` | Edit Application |
| POST | `/companions/me/application/submit` | Submit Application |
| POST | `/companions/me/application/withdraw` | Withdraw Application |
| POST | `/companions/me/deactivate` | Deactivate |
| PUT | `/companions/me/location` | Update Location |
| GET | `/companions/me/profile` | Get Profile |
| POST | `/companions/me/profile` | Create Profile |
| PUT | `/companions/me/profile` | Update Profile |
| POST | `/companions/me/profile/submit` | Submit Profile |
| GET | `/companions/me/status` | Get Status |

## discovery

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/discovery/companions` | Search |
| GET | `/discovery/companions/{profile_id}` | Companion Profile |
| GET | `/discovery/companions/{profile_id}/availability` | Companion Availability |
| GET | `/discovery/home` | Home |

## disputes

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/bookings/{booking_id}/dispute` | Get Dispute |
| POST | `/bookings/{booking_id}/dispute` | Create Dispute |
| POST | `/disputes/{dispute_id}/evidence` | Add Note |
| POST | `/disputes/{dispute_id}/evidence/image` | Add Image |

## favorites

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/favorites/companions` | List Favorites |
| DELETE | `/favorites/companions/{profile_id}` | Remove Favorite |
| PUT | `/favorites/companions/{profile_id}` | Add Favorite |
| GET | `/favorites/products` | Favorite Products |
| DELETE | `/favorites/products/{product_id}` | Remove Favorite |
| PUT | `/favorites/products/{product_id}` | Add Favorite |

## gifts

| Method | Path | Summary |
| --- | --- | --- |
| DELETE | `/gifts/cart` | Clear Cart |
| GET | `/gifts/cart` | Get Cart |
| DELETE | `/gifts/cart/items/{product_id}` | Remove Cart Item |
| PUT | `/gifts/cart/items/{product_id}` | Set Cart Item |
| GET | `/gifts/categories` | Categories |
| GET | `/gifts/orders` | My Orders |
| GET | `/gifts/orders/{order_id}` | Order Detail |
| POST | `/gifts/orders/{order_id}/cancel` | Cancel Order |
| POST | `/gifts/orders/{order_id}/review` | Review Order |
| GET | `/gifts/products` | Products |
| GET | `/gifts/products/{product_id}` | Product Page |

## health

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/health/ready` | Readiness |

## meeting

| Method | Path | Summary |
| --- | --- | --- |
| POST | `/bookings/{booking_id}/check-in` | Check In Route |
| POST | `/bookings/{booking_id}/end` | End Route |
| POST | `/bookings/{booking_id}/no-show` | No Show Route |
| POST | `/bookings/{booking_id}/start` | Start Route |

## notifications

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/notifications` | List Notifications |
| PUT | `/notifications/devices` | Register Device |
| POST | `/notifications/devices/remove` | Remove Device |
| POST | `/notifications/read-all` | Mark All Read |
| GET | `/notifications/unread-count` | Unread Count |
| POST | `/notifications/{notification_id}/read` | Mark Read |

## other

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/health` | Liveness |

## payments

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/payments` | My Payments |
| POST | `/payments/bookings/{booking_id}/checkout` | Checkout Booking |
| POST | `/payments/gifts/checkout` | Checkout Gifts |
| POST | `/payments/webhooks/{provider_name}` | Provider Webhook |
| GET | `/payments/{payment_id}` | Get Payment |

## payouts

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/payouts/me` | My Earnings |

## reviews

| Method | Path | Summary |
| --- | --- | --- |
| POST | `/bookings/{booking_id}/review` | Create Review |
| GET | `/bookings/{booking_id}/reviews` | Booking Reviews |
| GET | `/discovery/companions/{profile_id}/reviews` | Companion Reviews |
| GET | `/reviews/me` | My Reviews |

## safety

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/blocks` | List Blocks |
| DELETE | `/blocks/{user_id}` | Unblock User |
| PUT | `/blocks/{user_id}` | Block User |
| POST | `/bookings/{booking_id}/share` | Share Booking |
| POST | `/reports` | Create Report |
| GET | `/reports/me` | My Reports |
| GET | `/safety/center` | Safety Center |
| GET | `/safety/contacts` | List Contacts |
| POST | `/safety/contacts` | Add Contact |
| DELETE | `/safety/contacts/{contact_id}` | Delete Contact |
| PUT | `/safety/contacts/{contact_id}` | Update Contact |
| GET | `/safety/shared/{token}` | Shared Booking |
| POST | `/safety/sos` | Raise Sos |

## vendor panel

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/vendors/me` | Get Vendor |
| POST | `/vendors/me` | Apply |
| PUT | `/vendors/me` | Update Vendor |
| GET | `/vendors/me/orders` | Vendor Orders |
| POST | `/vendors/me/orders/{order_id}/status` | Update Order Status |
| GET | `/vendors/me/products` | List Products |
| POST | `/vendors/me/products` | Create Product |
| DELETE | `/vendors/me/products/{product_id}` | Deactivate Product |
| PUT | `/vendors/me/products/{product_id}` | Update Product |
| POST | `/vendors/me/products/{product_id}/images` | Upload Image |
| DELETE | `/vendors/me/products/{product_id}/images/{image_id}` | Delete Image |
| PUT | `/vendors/me/products/{product_id}/stock` | Set Stock |
| GET | `/vendors/me/ratings` | Ratings |

## verification

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/verification/me` | My Verification |
| POST | `/verification/me` | Start Verification |
| POST | `/verification/me/document` | Upload Document |
| POST | `/verification/me/selfie` | Upload Selfie |
| POST | `/verification/me/submit` | Submit Verification |

## Realtime

`GET /api/v1/realtime/ws` (WebSocket): send `{"type": "auth", "access_token": "..."}` first;
the server answers `{"type": "ready"}` and then streams `chat_message`, `booking_updated`
and `notification` events for the signed-in user. Send `ping` to receive `pong`.
