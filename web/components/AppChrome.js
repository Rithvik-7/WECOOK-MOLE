"use client";

import { MoleDock } from "./MoleDock";

export function AppChrome({ children }) {
  return (
    <>
      {children}
      <MoleDock />
    </>
  );
}
