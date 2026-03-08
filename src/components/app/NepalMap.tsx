import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
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

interface NepalMapProps {
  markers?: MapMarker[];
  height?: string;
}

export function NepalMap({ markers = [], height = "h-80" }: NepalMapProps) {
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
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
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
