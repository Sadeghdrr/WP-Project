/* Side-effect CSS import — loads all UI component styles */
import './ui.css';

/* ── Primitives ──────────────────────────────────────────────────── */

export { Button } from './Button';
export type { ButtonProps } from './Button';

export { Input, Textarea } from './Input';
export type { InputProps, TextareaProps } from './Input';

export { Select } from './Select';
export type { SelectProps, SelectOption } from './Select';

export { Badge } from './Badge';
export type { BadgeProps } from './Badge';

export { Skeleton } from './Skeleton';
export type { SkeletonProps } from './Skeleton';

export { Loader } from './Loader';
export type { LoaderProps } from './Loader';

/* ── Composites ──────────────────────────────────────────────────── */

export { Card } from './Card';
export type { CardProps } from './Card';

export { Modal } from './Modal';
export type { ModalProps } from './Modal';

export { Drawer } from './Drawer';
export type { DrawerProps } from './Drawer';

export { Table } from './Table';
export type { TableProps, Column } from './Table';

export { Pagination } from './Pagination';
export type { PaginationProps } from './Pagination';

export { Tabs } from './Tabs';
export type { TabsProps, TabItem } from './Tabs';

export { Alert } from './Alert';
export type { AlertProps } from './Alert';
