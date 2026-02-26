interface EvidenceGalleryProps {
  screenshots: string[];
}

export function EvidenceGallery({ screenshots }: EvidenceGalleryProps): JSX.Element {
  if (screenshots.length === 0) {
    return <p>No screenshots captured.</p>;
  }
  return (
    <section>
      <h4>Evidence Gallery</h4>
      <div className="gallery">
        {screenshots.map((shot) => (
          <figure key={shot}>
            <img src={`/evidence/${shot}`} alt={shot} />
            <figcaption>{shot}</figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
