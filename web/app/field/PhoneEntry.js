"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FieldDesk } from "../../components/FieldDesk";

const KEY = "mole-phone-entry";

export function PhoneEntry() {
  const params = useSearchParams();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const allowed =
      params.get("entry") === "phone" || sessionStorage.getItem(KEY) === "1";
    if (params.get("entry") === "phone") sessionStorage.setItem(KEY, "1");
    if (!allowed) {
      router.replace("/");
      return;
    }
    setOpen(true);
  }, [params, router]);

  if (!open) return null;
  return <FieldDesk />;
}
