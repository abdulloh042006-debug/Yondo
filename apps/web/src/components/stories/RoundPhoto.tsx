import type { Schemas } from '../../api/client';
import { usePublicPhotoUrl } from '../../pages/companionParts';
import { Avatar } from '../avatar/Avatar';

type Photo = Schemas['DiscoveryPhoto'];

/** Round companion photo; the geometric avatar (seed = profile id) stands in when there is none. Decorative. */
export function RoundPhoto({ profileId, photo, size }: { profileId: string; photo?: Photo | null; size: 32 | 44 | 64 }) {
  const url = usePublicPhotoUrl(profileId, photo);
  if (url) return <img className="st-photo" src={url} alt="" width={size} height={size} style={{ width: size, height: size }} />;
  return <Avatar seed={profileId} size={size} />;
}
