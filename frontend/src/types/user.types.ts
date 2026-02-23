/**
 * User and Role types — mirror backend accounts app (UserDetailSerializer, RoleListSerializer).
 * DO NOT modify without verifying backend DTOs.
 */

export interface RoleDetail {
  id: number;
  name: string;
  description: string;
  hierarchy_level: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  national_id: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
  role: number;
  role_detail: RoleDetail;
  permissions: string[];
}

export interface UserProfile extends User {}
