/**
 * Tabs — tabbed interface supporting controlled and uncontrolled modes.
 */
import { useState, type ReactNode } from 'react';

export interface TabItem {
  key: string;
  label: string;
  content: ReactNode;
  disabled?: boolean;
  icon?: ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeKey?: string;
  defaultActiveKey?: string;
  onChange?: (key: string) => void;
  className?: string;
}

export function Tabs({
  tabs,
  activeKey: controlledKey,
  defaultActiveKey,
  onChange,
  className = '',
}: TabsProps) {
  const [internalKey, setInternalKey] = useState(
    defaultActiveKey ?? tabs[0]?.key ?? '',
  );

  const activeKey = controlledKey ?? internalKey;

  const handleSelect = (key: string) => {
    if (controlledKey === undefined) setInternalKey(key);
    onChange?.(key);
  };

  const activeTab = tabs.find((t) => t.key === activeKey);

  return (
    <div className={`tabs ${className}`}>
      <div className="tabs__list" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={tab.key === activeKey}
            aria-controls={`tabpanel-${tab.key}`}
            className={`tabs__tab ${tab.key === activeKey ? 'tabs__tab--active' : ''}`}
            onClick={() => handleSelect(tab.key)}
            disabled={tab.disabled}
          >
            {tab.icon && <span className="tabs__tab-icon">{tab.icon}</span>}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab && (
        <div
          id={`tabpanel-${activeTab.key}`}
          role="tabpanel"
          className="tabs__panel"
        >
          {activeTab.content}
        </div>
      )}
    </div>
  );
}
