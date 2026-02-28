/**
 * 审批/单据流转可视化：横向或纵向步骤条，展示当前节点与状态
 */
export interface FlowStep {
  key: string;
  label: string;
  status: "pending" | "current" | "done";
  time?: string;
}

interface FlowStepsProps {
  steps: FlowStep[];
  direction?: "horizontal" | "vertical";
  "aria-label"?: string;
}

export function FlowSteps({
  steps,
  direction = "horizontal",
  "aria-label": ariaLabel = "流程步骤",
}: FlowStepsProps) {
  return (
    <nav
      className={"flow-steps flow-steps--" + direction}
      aria-label={ariaLabel}
      style={{
        display: "flex",
        flexDirection: direction === "horizontal" ? "row" : "column",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      {steps.map((step, index) => (
        <div
          key={step.key}
          className={"flow-step flow-step--" + step.status}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span
            className="flow-step__marker"
            aria-hidden="true"
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              border: "2px solid",
              borderColor: step.status === "done" ? "var(--color-success)" : step.status === "current" ? "var(--color-primary)" : "var(--color-border)",
              background: step.status === "done" ? "var(--color-success)" : step.status === "current" ? "var(--color-primary)" : "transparent",
              color: step.status === "pending" ? "var(--color-text-muted)" : "#fff",
              fontSize: 12,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {step.status === "done" ? "✓" : index + 1}
          </span>
          <span>
            <span style={{ fontWeight: step.status === "current" ? 600 : 400 }}>{step.label}</span>
            {step.time && (
              <span style={{ fontSize: 12, color: "var(--color-text-muted)", marginLeft: 8 }}>{step.time}</span>
            )}
          </span>
          {direction === "horizontal" && index < steps.length - 1 && (
            <span
              aria-hidden="true"
              style={{
                width: 20,
                height: 2,
                background: step.status === "done" ? "var(--color-success)" : "var(--color-border)",
              }}
            />
          )}
        </div>
      ))}
    </nav>
  );
}
