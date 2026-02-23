import React from 'react';

export interface CardProps {
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ title, children, footer, className = '' }) => {
  return (
    <div
      className={`rounded-xl border border-slate-700 bg-slate-800/80 shadow-xl ${className}`}
    >
      {title && (
        <div className="border-b border-slate-700 px-6 py-4">
          <h2 className="text-right text-lg font-semibold text-slate-100">{title}</h2>
        </div>
      )}
      <div className="p-6">{children}</div>
      {footer && (
        <div className="border-t border-slate-700 px-6 py-4">{footer}</div>
      )}
    </div>
  );
};
