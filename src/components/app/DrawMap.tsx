import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { Card } from "@/components/ui/card";
import { COMMUNITY_FORESTS } from "@/lib/nepal-locations";

// Fix default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const NEPAL_BOUNDS: [[number, number], [number, number]] = [
  [26.347, 80.058],
  [30.447, 88.201],
];

const forestIcon = new L.DivIcon({
  html: '<div style="background:hsl(153,40%,42%);border:2px solid #fff;border-radius:50%;width:12px;height:12px;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>',
  className: "",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

function FitNepal() {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(NEPAL_BOUNDS, { padding: [20, 20] });
  }, [map]);
  return null;
}

function DrawControl({ onCreated }: { onCreated: (geojson: GeoJSON.GeoJSON) => void }) {
  const map = useMap();
  const drawnRef = useRef<L.FeatureGroup | null>(null);

  useEffect(() => {
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

interface DrawMapProps {
  onPolygonCreated: (geojson: GeoJSON.GeoJSON) => void;
  height?: string;
}

export function DrawMap({ onPolygonCreated, height = "h-80" }: DrawMapProps) {
  const forests = Object.entries(COMMUNITY_FORESTS);

  return (
    <Card className="shadow-card overflow-hidden">
      <div className="px-4 py-2.5 bg-card border-b border-border">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Draw AOI — Click the polygon tool (▰) on the right to begin
        </p>
      </div>
      <div className={height}>
        <MapContainer
          center={[28.3949, 84.124]}
          zoom={7}
          className="h-full w-full z-0"
          scrollWheelZoom={true}
        >
          <FitNepal />
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          {forests.map(([name, loc]) => (
            <Marker key={name} position={[loc.lat, loc.lon]} icon={forestIcon}>
              <Popup>
                <span className="font-medium text-xs">{name}</span>
              </Popup>
            </Marker>
          ))}
          <DrawControl onCreated={onPolygonCreated} />
        </MapContainer>
      </div>
      <div className="px-4 py-2 bg-card border-t border-border flex items-center gap-3">
        <span className="inline-block w-3 h-3 rounded-full" style={{ background: "hsl(153,40%,42%)", border: "2px solid #fff" }} />
        <span className="text-[10px] text-muted-foreground">Community Forests / Protected Areas</span>
      </div>
    </Card>
  );
}
