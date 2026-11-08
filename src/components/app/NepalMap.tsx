import { useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  Polygon,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Card } from "@/components/ui/card";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const NEPAL_CENTER: [number, number] = [28.3949, 84.124];
const NEPAL_BOUNDS: [[number, number], [number, number]] = [
  [26.347, 80.058],
  [30.447, 88.201],
];

export type LatLon = { lat: number; lon: number };

interface MapMarker {
  lat: number;
  lon: number;
  label: string;
}

function FitNepal({ disabled }: { disabled?: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!disabled) map.fitBounds(NEPAL_BOUNDS, { padding: [20, 20] });
  }, [map, disabled]);
  return null;
}

function FocusOn({ center, zoom }: { center?: LatLon | null; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.setView([center.lat, center.lon], zoom ?? 11);
  }, [map, center?.lat, center?.lon, zoom]);
  return null;
}

function DrawClickHandler({
  enabled,
  onAddPoint,
}: {
  enabled: boolean;
  onAddPoint?: (point: LatLon) => void;
}) {
  useMapEvents({
    click(e) {
      if (!enabled || !onAddPoint) return;
      onAddPoint({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
  });
  return null;
}

function NdviTileLayer({ urlTemplate }: { urlTemplate?: string | null }) {
  const map = useMap();
  useEffect(() => {
    if (!urlTemplate) return;
    const layer = L.tileLayer(urlTemplate, {
      opacity: 0.65,
      maxZoom: 18,
      attribution: "NDVI · Sentinel-2 via GEE",
    });
    layer.addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, urlTemplate]);
  return null;
}

interface NepalMapProps {
  markers?: MapMarker[];
  height?: string;
  center?: LatLon | null;
  radiusKm?: number;
  showCircle?: boolean;
  drawMode?: boolean;
  drawPoints?: LatLon[];
  onAddDrawPoint?: (point: LatLon) => void;
  tileUrl?: string | null;
  fitNepal?: boolean;
}

export function NepalMap({
  markers = [],
  height = "h-80",
  center = null,
  radiusKm = 5,
  showCircle = false,
  drawMode = false,
  drawPoints = [],
  onAddDrawPoint,
  tileUrl = null,
  fitNepal = true,
}: NepalMapProps) {
  const polygonPositions = useMemo(
    () => drawPoints.map((p) => [p.lat, p.lon] as [number, number]),
    [drawPoints],
  );

  return (
    <Card className="shadow-card overflow-hidden">
      <div className={height}>
        <MapContainer
          center={center ? [center.lat, center.lon] : NEPAL_CENTER}
          zoom={center ? 11 : 7}
          className={`h-full w-full z-0 ${drawMode ? "cursor-crosshair" : ""}`}
          scrollWheelZoom
        >
          {fitNepal && !center && <FitNepal />}
          {center && <FocusOn center={center} zoom={11} />}
          <TileLayer
            attribution="Tiles &copy; Esri"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          <NdviTileLayer urlTemplate={tileUrl} />
          <DrawClickHandler enabled={drawMode} onAddPoint={onAddDrawPoint} />

          {showCircle && center && !drawMode && (
            <Circle
              center={[center.lat, center.lon]}
              radius={radiusKm * 1000}
              pathOptions={{ color: "#FFD700", weight: 2.5, fill: false }}
            />
          )}

          {polygonPositions.length >= 2 && (
            <Polygon
              positions={polygonPositions}
              pathOptions={{ color: "#FFD700", weight: 2.5, fillColor: "#FFD700", fillOpacity: 0.15 }}
            />
          )}

          {drawPoints.map((p, i) => (
            <Marker key={`draw-${i}`} position={[p.lat, p.lon]}>
              <Popup>
                Point {i + 1}: {p.lat.toFixed(4)}, {p.lon.toFixed(4)}
              </Popup>
            </Marker>
          ))}

          {markers.map((m, i) => (
            <Marker key={i} position={[m.lat, m.lon]}>
              <Popup>
                <span className="font-medium text-sm">{m.label}</span>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </Card>
  );
}
