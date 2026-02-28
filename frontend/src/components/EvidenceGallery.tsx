import type { RunEvidence } from "../types/Run";

interface EvidenceGalleryProps {
  screenshots: string[] | RunEvidence[];
}

export function EvidenceGallery({ screenshots }: EvidenceGalleryProps): JSX.Element {
  if (screenshots.length === 0) {
    return <p>No screenshots captured.</p>;
  }
  return (
    <section>
      <h4>Evidence Gallery</h4>
      <div className="gallery">
        {screenshots.map((shot, index) => {
          const item =
            typeof shot === "string"
              ? { src: shot.startsWith("/") ? shot : `/evidence/${shot}`, label: shot.replace(/^.*\//, "") }
              : shot;
          return (
          <figure key={`${item.src}-${index}`}>
            <img src={item.src} alt={item.label} loading="lazy" />
            <figcaption>{item.label}</figcaption>
          </figure>
          );
        })}
      </div>
    </section>
  );
}
