// TODO: Define Suspect, Interrogation, Trial, BountyTip, Bail interfaces
// Should mirror backend suspects app models

export interface Suspect {
  // TODO: id, case, user, national_id, full_name, photo, status,
  //       most_wanted_score, reward_amount, is_most_wanted
}

export interface Interrogation {
  // TODO: suspect, interrogator, guilt_score (1-10), notes, timestamp
}

export interface Trial {
  // TODO: suspect, judge, verdict (guilty/innocent), punishment_title,
  //       punishment_description
}

export interface BountyTip {
  // TODO: suspect/case, submitted_by, info, status, unique_code
}

export interface Bail {
  // TODO: suspect, amount, approved_by (sergeant), payment_status
}

export enum SuspectStatus {
  // TODO: WANTED, ARRESTED, UNDER_INTERROGATION, UNDER_TRIAL, CONVICTED, ACQUITTED, RELEASED
}

export enum VerdictChoice {
  // TODO: GUILTY, INNOCENT
}

export enum BountyTipStatus {
  // TODO: PENDING, OFFICER_REVIEWED, VERIFIED, REJECTED
}
