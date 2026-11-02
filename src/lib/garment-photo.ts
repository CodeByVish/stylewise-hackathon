export type GarmentPhoto = { data: string; source: string; filename: string };
export function readGarmentPhoto(file: File): Promise<GarmentPhoto> {
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 5_000_000) {
    return Promise.reject(new Error('Choose a PNG, JPEG or WebP image smaller than 5 MB.'));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read this photo. Try another file.'));
    reader.onload = () => {
      const data = String(reader.result);
      const image = new Image();
      image.onerror = () => reject(new Error('This file could not be opened as an image.'));
      image.onload = () => resolve({ data, filename: file.name, source: file.name });
      image.src = data;
    };
    reader.readAsDataURL(file);
  });
}
