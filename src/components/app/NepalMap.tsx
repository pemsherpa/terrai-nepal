import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { Card } from "@/components/ui/card";

// Fix default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
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

interface MapMarker {
  lat: number;
  lon: number;
  label: string;
}

function FitNepal() {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(NEPAL_BOUNDS, { padding: [20, 20] });
  }, [map]);
  return null;
}

/** Draw control – loaded dynamically to avoid SSR issues with leaflet-draw */
function DrawControl({ onCreated }: { onCreated: (geojson: GeoJSON.GeoJSON) => void }) {
  const map = useMap();
  const drawnRef = useRef<L.FeatureGroup | null>(null);

  useEffect(() => {
    // Dynamic import to avoid module-level side effects
    import("leaflet-draw").then(() => {
      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);
      drawnRef.current = drawnItems;

      const drawControl = new (L.Control as any).Draw({
        position: "topright",
        draw: {
          polygon: {
            allowIntersection: false,
            shapeOptions: { color: "#FFD700", fillColor: "#27AE60", fillOpacity: 0.4 },
          },
          polyline: false,
          rectangle: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: { featureGroup: drawnItems },
      });
      map.addControl(drawControl);

      map.on(L.Draw.Event.CREATED as any, (e: any) => {
        drawnItems.clearLayers();
        const layer = e.layer;
        drawnItems.addLayer(layer);
        onCreated(layer.toGeoJSON());
      });

      return () => {
        map.removeControl(drawControl);
        map.removeLayer(drawnItems);
      };
    });
  }, [map, onCreated]);

  return null;
}

interface NepalMapProps {
  markers?: MapMarker[];
  height?: string;
  circleCenter?: [number, number] | null;
  circleRadiusKm?: number;
  drawMode?: boolean;
  onPolygonCreated?: (geojson: GeoJSON.GeoJSON) => void;
  tileUrl?: string;
}

export function NepalMap({
  markers = [],
  height = "h-80",
  circleCenter = null,
  circleRadiusKm = 5,
  drawMode = false,
  onPolygonCreated,
  tileUrl,
}: NepalMapProps) {
  return (
    <Card className="shadow-card overflow-hidden">
      <div className={height}>
        <MapContainer
          center={NEPAL_CENTER}
          zoom={7}
          className="h-full w-full z-0"
          scrollWheelZoom={true}
        >
          <FitNepal />
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          {markers.map((m, i) => (
            <Marker key={i} position={[m.lat, m.lon]}>
              <Popup>
                <span className="font-medium text-sm">{m.label}</span>
              </Popup>
            </Marker>
          ))}
          {circleCenter && (
            <Circle
              center={circleCenter}
              radius={circleRadiusKm * 1000}
              pathOptions={{
                color: "#FFD700",
                fillColor: "#27AE60",
                fillOpacity: 0.4,
                weight: 2,
              }}
            />
          )}
          {drawMode && onPolygonCreated && (
            <DrawControl onCreated={onPolygonCreated} />
          )}
        </MapContainer>
      </div>
      {/* NDVI Legend */}
      <div className="px-4 py-3 bg-card border-t border-border">
        <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
          <span>NDVI Legend</span>
        </div>
        <div className="h-3 rounded-full overflow-hidden" style={{
          background: "linear-gradient(to right, hsl(0 70% 50%), hsl(30 80% 55%), hsl(50 80% 55%), hsl(90 50% 55%), hsl(140 50% 35%))"
        }} />
        <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
          <span>0.0 Bare</span>
          <span>0.25</span>
          <span>0.5</span>
          <span>0.75</span>
          <span>1.0 Dense</span>
        </div>
      </div>
    </Card>
  );
}
