import "@fontsource/lexend/500.css";
import "@fontsource/lexend/600.css";
import "@fontsource/lexend/700.css";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "./globals.css";
import "./appearance.css";
import { OfflineRegistration } from "../components/OfflineRegistration";
import { AppChrome } from "../components/AppChrome";

export const metadata = {
  title: "MOLE",
  icons: { icon: "/mole-icon.svg" },
  description: "Surface monitoring for underground mining movement.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <OfflineRegistration />
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
