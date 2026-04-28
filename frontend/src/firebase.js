import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
  measurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID
};

const app = initializeApp(firebaseConfig);
export const analytics = getAnalytics(app);
export const auth = getAuth(app);

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: "select_account",
  hd: "vitapstudent.ac.in",
});

export async function signInWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  const email = result.user.email || "";
  if (!email.endsWith("@vitapstudent.ac.in")) {
    await result.user.delete().catch(() => {});
    await auth.signOut().catch(() => {});
    throw new Error("Only @vitapstudent.ac.in accounts are allowed.");
  }
  const idToken = await result.user.getIdToken();
  return { idToken, user: result.user };
}
