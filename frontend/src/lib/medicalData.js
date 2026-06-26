/**
 * Curated Medical Knowledge Base
 * Used for Autocomplete dropdowns to standardize AI inputs and apply IRDAI rules.
 */

export const CITIES = [
  "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata", "Surat", "Pune", "Jaipur",
  "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara"
];

export const PROCEDURES = [
  "Appendectomy",
  "CABG (Coronary Artery Bypass Graft)",
  "PTCA (Percutaneous Transluminal Coronary Angioplasty)",
  "Cataract Surgery",
  "Total Knee Replacement (TKR)",
  "Total Hip Replacement (THR)",
  "Dengue Fever Treatment",
  "Malaria Treatment",
  "Maternity (Normal Delivery)",
  "Maternity (C-Section)",
  "Gallbladder Removal (Cholecystectomy)",
  "Hysterectomy",
  "Hernia Repair",
  "Dialysis",
  "Chemotherapy",
  "Radiotherapy",
  "Tonsillectomy",
  "Kidney Stone Removal",
  "COVID-19 Treatment"
];

export const HOSPITALS = [
  // Mumbai
  { name: "Apollo Hospitals, Navi Mumbai", city: "Mumbai", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO", "Care Health"] },
  { name: "Lilavati Hospital", city: "Mumbai", acceptedInsurers: ["ICICI Lombard", "HDFC ERGO"] },
  { name: "Kokilaben Dhirubhai Ambani Hospital", city: "Mumbai", acceptedInsurers: ["Star Health", "ICICI Lombard", "Niva Bupa"] },
  { name: "Breach Candy Hospital", city: "Mumbai", acceptedInsurers: ["HDFC ERGO", "Star Health"] },
  
  // Delhi
  { name: "AIIMS New Delhi", city: "Delhi", acceptedInsurers: ["Star Health", "ICICI Lombard", "Care Health"] },
  { name: "Max Super Speciality Hospital, Saket", city: "Delhi", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO", "Niva Bupa"] },
  { name: "Indraprastha Apollo Hospitals", city: "Delhi", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO"] },
  { name: "Sir Ganga Ram Hospital", city: "Delhi", acceptedInsurers: ["ICICI Lombard", "Care Health"] },

  // Bengaluru
  { name: "Manipal Hospital, Old Airport Road", city: "Bengaluru", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO"] },
  { name: "Fortis Hospital, Bannerghatta Road", city: "Bengaluru", acceptedInsurers: ["Star Health", "ICICI Lombard"] },
  { name: "Narayana Health City", city: "Bengaluru", acceptedInsurers: ["Star Health", "ICICI Lombard", "Care Health", "Niva Bupa"] },

  // Hyderabad
  { name: "Apollo Hospitals, Jubilee Hills", city: "Hyderabad", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO"] },
  { name: "KIMS Hospitals", city: "Hyderabad", acceptedInsurers: ["Star Health", "ICICI Lombard", "Care Health"] },
  { name: "Yashoda Hospitals", city: "Hyderabad", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO", "Niva Bupa"] },

  // Chennai
  { name: "Apollo Hospitals, Greams Road", city: "Chennai", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO", "Care Health"] },
  { name: "Fortis Malar Hospital", city: "Chennai", acceptedInsurers: ["Star Health", "ICICI Lombard"] },
  { name: "MIOT International", city: "Chennai", acceptedInsurers: ["Star Health", "ICICI Lombard", "Niva Bupa"] },

  // Jaipur
  { name: "Fortis Escorts Hospital", city: "Jaipur", acceptedInsurers: ["Star Health", "ICICI Lombard"] },
  { name: "Narayana Multispeciality Hospital", city: "Jaipur", acceptedInsurers: ["Star Health", "ICICI Lombard", "Care Health"] },

  // Pune
  { name: "Ruby Hall Clinic", city: "Pune", acceptedInsurers: ["Star Health", "ICICI Lombard", "HDFC ERGO"] },
  { name: "Jehangir Hospital", city: "Pune", acceptedInsurers: ["Star Health", "ICICI Lombard"] }
];
