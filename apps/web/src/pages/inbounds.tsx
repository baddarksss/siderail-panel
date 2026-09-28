import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Router, Waypoints, Network, Lock, Pencil } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Inbound } from "@/lib/types";

const protocolAccent: Record<string, string> = {
  vless: "#a3e635",
  vmess: "#7dd3fc",
  trojan: "#f0abfc",
};

export default function InboundsPage() {
  const toast = useToast();
  const { t } = useI18n();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Inbound | null>(null);
  const [form, setForm] = useState<{ label: string; tag: string; path: string }>({
    label: "",
    tag: "",
    path: "",
  });

  const { data: inbounds = [] } = useQuery<Inbound[]>({
    queryKey: ["inbounds"],
    queryFn: api.inbounds,
    refetchInterval: 10000,
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      api.toggleInbound(id, enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inbounds"] });
      toast.push("success", t("inboundUpdated"));
    },
    onError: (e: Error) => toast.push("error", e.message),
  });

  const save = useMutation({
    mutationFn: () =>
      api.updateInbound(editing!.id, {
        label: form.label,
        tag: form.tag,
        path: form.path,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inbounds"] });
      toast.push("success", t("inboundSaved"));
      setEditing(null);
    },
    onError: (e: Error) => toast.push("error", e.message),
  });

  const openEdit = (ib: Inbound) => {
    setForm({ label: ib.label || "", tag: ib.tag, path: ib.path });
    setEditing(ib);
  };

  const enabledCount = inbounds.filter((i) => i.enabled).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl">{t("inbounds")}</h1>
          <p className="text-sm font-base text-text/60">{t("inboundsDesc")}</p>
        </div>
        <Badge variant="info" className="h-9 gap-1.5 px-3">
          <Waypoints className="h-4 w-4 shrink-0" />
          {enabledCount} / {inbounds.length} {t("enabledCount")}
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {inbounds.map((ib) => (
          <Card
            key={ib.id}
            className="overflow-hidden transition-transform hover:-translate-y-0.5"
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <div
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-base border-2 border-border font-heading text-sm uppercase text-black"
                    style={{ background: protocolAccent[ib.protocol] || "#a3e635" }}
                  >
                    {ib.protocol.slice(0, 2)}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate font-heading text-sm">{ib.label || ib.tag}</div>
                    {ib.label ? (
                      <div className="truncate font-mono text-[10px] text-text/50">{ib.tag}</div>
                    ) : null}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title={t("inboundEditTitle")}
                    onClick={() => openEdit(ib)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Switch
                    checked={!!ib.enabled}
                    onCheckedChange={(v) => toggle.mutate({ id: ib.id, enabled: v })}
                  />
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-1.5">
                <Badge variant="neutral" className="justify-center truncate text-[10px] uppercase">
                  {ib.protocol}
                </Badge>
                <Badge variant="default" className="justify-center truncate text-[10px] uppercase">
                  {ib.transport}
                </Badge>
                <Badge variant="success" className="justify-center gap-1 text-[10px]">
                  <Lock className="h-3 w-3 shrink-0" /> TLS 443
                </Badge>
              </div>
              <div className="mt-3 space-y-1.5 border-t-2 border-border/30 pt-2.5 text-[11px] font-base text-text/60">
                <div className="flex items-center gap-2">
                  <Network className="h-3.5 w-3.5 shrink-0" />
                  <span className="shrink-0">{t("port")}</span>
                  <span className="ml-auto font-mono text-text/80">{ib.port}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Router className="h-3.5 w-3.5 shrink-0" />
                  <span className="shrink-0">{t("path")}</span>
                  <span className="ml-auto min-w-0 truncate font-mono text-text/80">{ib.path}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t("inboundEditTitle")}</DialogTitle>
          </DialogHeader>
          <p className="-mt-2 text-xs font-base text-text/60">{t("inboundEditHint")}</p>
          <div className="space-y-3">
            <div>
              <Label htmlFor="ib-label">{t("inboundLabel")}</Label>
              <Input
                id="ib-label"
                value={form.label}
                placeholder={editing?.tag || ""}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="ib-tag">{t("inboundTag")}</Label>
              <Input
                id="ib-tag"
                value={form.tag}
                onChange={(e) => setForm({ ...form, tag: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="ib-path">{t("path")}</Label>
              <Input
                id="ib-path"
                value={form.path}
                className="font-mono"
                onChange={(e) => setForm({ ...form, path: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="neutral" onClick={() => setEditing(null)}>
              {t("cancel")}
            </Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? t("saving") : t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
