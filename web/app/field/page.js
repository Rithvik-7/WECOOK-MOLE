import { Suspense } from "react";
import { PhoneEntry } from "./PhoneEntry";

export const metadata = {
  title: "Alerts and reports · MOLE",
  description: "Alerts and issue reports for miners and residents at East Panel.",
};

export default function Page() {
  return (
    <Suspense fallback={null}>
      <PhoneEntry />
    </Suspense>
  );
}
