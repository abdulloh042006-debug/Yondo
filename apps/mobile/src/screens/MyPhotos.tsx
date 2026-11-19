import * as ImagePicker from 'expo-image-picker';

import { SafeImage } from '../safeImage';
import { useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';

import { api, errorText, type Schemas } from '../api';
import { moveId, photoProblem, PHOTO_LIMIT } from '../photoRules';
import { t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, ConfirmDialog, ErrorText, H2, P, Row, Tag } from '../ui';
import { useResource } from '../useResource';

type Photo = Schemas['UserPhotoResponse'];

/**
 * Profil → "Rasmlarim" (the web's ui/MyPhotos.tsx): up to 6 photos of the signed-in user, `/user-photos/me`.
 * The first is the main photo. A customer's photos are private (companions the customer sent a booking request to,
 * and moderators; the server enforces it). A companion's public card photos are managed in the studio (web).
 */
export function MyPhotos({ isCompanion, onStudio }: { isCompanion: boolean; onStudio: () => void }) {
  const { palette } = useTheme();
  const res = useResource(() => api.get<Photo[]>('/user-photos/me'), []);
  const [uploading, setUploading] = useState(false);
  const [ordering, setOrdering] = useState(false);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [removing, setRemoving] = useState<Photo | null>(null);
  const [removeBusy, setRemoveBusy] = useState(false);
  const photos = res.data ?? [];
  const full = photos.length >= PHOTO_LIMIT;
  const ids = photos.map((p) => p.id);

  const pick = async () => {
    setError(undefined);
    setNotice(undefined);
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsMultipleSelection: false, quality: 1 });
    if (picked.canceled || !picked.assets?.[0]) return;
    const asset = picked.assets[0];
    let blob: Blob;
    try {
      blob = await (await fetch(asset.uri)).blob();
    } catch {
      return setError(t('common.actionFailed'));
    }
    const type = asset.mimeType || blob.type;
    const problem = photoProblem({ type, size: asset.fileSize ?? blob.size }, photos.length);
    if (problem) return setError(t(problem));
    setUploading(true);
    try {
      await api.upload<Photo>('/user-photos/me', blob, type);
      setNotice(t('photos.uploaded'));
      res.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setUploading(false);
    }
  };

  const reorder = async (next: string[], okText: string) => {
    if (ordering) return;
    setError(undefined);
    setNotice(undefined);
    setOrdering(true);
    const before = photos;
    res.setData(next.map((id, i) => ({ ...before.find((p) => p.id === id)!, position: i })));
    try {
      res.setData(await api.put<Photo[]>('/user-photos/me/order', { photo_ids: next }));
      setNotice(okText);
    } catch (e) {
      res.setData(before);
      setError(errorText(e));
    } finally {
      setOrdering(false);
    }
  };

  return (
    <Card style={{ gap: 10 }}>
      <H2>{`${t('photos.title')} · ${t('photos.count', { n: photos.length })}`}</H2>
      <P muted>{isCompanion ? t('photos.privacyCompanion') : t('photos.privacyCustomer')}</P>
      {isCompanion && (
        <Row>
          <Button kind="ghost" small label={t('account.studio')} onPress={onStudio} />
        </Row>
      )}
      <P muted>{full ? t('photos.limitErr') : t('photos.rules')}</P>
      <Row>
        <Button label={t('photos.upload')} busy={uploading} disabled={full || res.loading} onPress={() => void pick()} />
      </Row>
      {uploading && (
        <View role="progressbar" aria-label={t('photos.uploading')} aria-busy style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
          <ActivityIndicator color={palette.fg} />
          <Text style={{ color: palette.muted, fontFamily: FONT.body }}>{t('photos.uploading')}</Text>
        </View>
      )}
      {notice && <Banner text={notice} />}
      {error && <ErrorText text={error} />}
      {!!res.error && <ErrorText text={errorText(res.error)} />}
      {res.data && photos.length === 0 && (
        <View style={{ gap: 2 }}>
          <Text style={{ color: palette.fg, fontFamily: FONT.bold }}>{t('photos.empty')}</Text>
          <P muted>{t('photos.emptyBody')}</P>
        </View>
      )}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
        {photos.map((p, i) => (
          <View key={p.id} style={{ width: '47%', gap: 6, borderWidth: 1, borderColor: palette.glassLine, borderRadius: 16, padding: 6, backgroundColor: palette.glass }}>
            <OwnPhoto id={p.id} alt={t('photos.alt', { n: i + 1 })} />
            {i === 0 && (
              <View style={{ position: 'absolute', top: 12, left: 12 }}>
                <Tag text={t('photos.main')} attention />
              </View>
            )}
            <Row style={{ gap: 6 }}>
              <Button small kind="ghost" label="←" accessibilityLabel={t('photos.moveEarlier', { n: i + 1 })} disabled={i === 0 || ordering} onPress={() => void reorder(moveId(ids, p.id, i - 1), t('photos.orderSaved'))} />
              <Button small kind="ghost" label="→" accessibilityLabel={t('photos.moveLater', { n: i + 1 })} disabled={i === photos.length - 1 || ordering} onPress={() => void reorder(moveId(ids, p.id, i + 1), t('photos.orderSaved'))} />
            </Row>
            {i > 0 && <Button small kind="ghost" label={t('photos.makeMain')} disabled={ordering} onPress={() => void reorder(moveId(ids, p.id, 0), t('photos.mainSet'))} />}
            <Button small kind="ghost" label={t('common.delete')} onPress={() => setRemoving(p)} />
          </View>
        ))}
      </View>
      <ConfirmDialog open={!!removing} title={t('photos.removeTitle')} onClose={() => !removeBusy && setRemoving(null)}>
        <P>{t('photos.removeBody')}</P>
        <Row>
          <Button kind="ghost" label={t('common.cancel')} disabled={removeBusy} onPress={() => setRemoving(null)} />
          <Button
            kind="danger"
            label={t('common.delete')}
            busy={removeBusy}
            onPress={() => {
              setRemoveBusy(true);
              setError(undefined);
              api
                .del(`/user-photos/me/${removing!.id}`)
                .then(() => {
                  setNotice(t('photos.removed'));
                  setRemoving(null);
                  res.reload();
                })
                .catch((e: unknown) => {
                  setRemoving(null);
                  setError(errorText(e));
                })
                .finally(() => setRemoveBusy(false));
            }}
          />
        </Row>
      </ConfirmDialog>
    </Card>
  );
}

/** The owner's own photo through a short-lived signed URL. */
function OwnPhoto({ id, alt }: { id: string; alt: string }) {
  const { palette } = useTheme();
  const res = useResource(() => api.get<Schemas['PhotoDownload']>(`/user-photos/me/${id}/download`), [id]);
  const box = { width: '100%' as const, aspectRatio: 3 / 4, borderRadius: 12, backgroundColor: palette.chip };
  return <SafeImage src={res.data?.url ?? (res.error ? null : undefined)} style={box} alt={alt} />;
}
