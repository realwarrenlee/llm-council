"use client";

import * as React from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { OutputModeSelector } from "./output-mode-selector";
import { AnonymizationToggle } from "./anonymization-toggle";
import { Settings2 } from "lucide-react";

interface AdvancedOptionsProps {
  outputMode: "perspectives" | "synthesis" | "both";
  onOutputModeChange: (value: "perspectives" | "synthesis" | "both") => void;
  anonymize: boolean;
  onAnonymizeChange: (value: boolean) => void;
  disabled?: boolean;
}

export function AdvancedOptions({
  outputMode,
  onOutputModeChange,
  anonymize,
  onAnonymizeChange,
  disabled = false,
}: AdvancedOptionsProps) {
  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="advanced" className="border-none">
        <AccordionTrigger className="py-2 hover:no-underline">
          <div className="flex items-center gap-2 text-sm">
            <Settings2 className="h-4 w-4" />
            <span>Advanced Options</span>
          </div>
        </AccordionTrigger>
        <AccordionContent className="space-y-4 pt-2">
          <OutputModeSelector
            value={outputMode}
            onChange={onOutputModeChange}
            disabled={disabled}
          />
          <AnonymizationToggle
            value={anonymize}
            onChange={onAnonymizeChange}
            disabled={disabled}
          />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
