import React, { useState, useEffect } from "react";

import {
  View,
  Text,
  Button,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform
} from "react-native";

import * as ImagePicker from "expo-image-picker";
import axios from "axios";

export default function App() {

  const [file, setFile] = useState<any>(null);
  const [result, setResult] = useState("No result yet");
  const [loading, setLoading] = useState(false);

  // ✅ YOUR PERMANENT BACKEND
  const SERVER_URL = "https://videogpt-app.onrender.com/process";

  // ================= PERMISSION =================

  useEffect(() => {

    (async () => {

      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        Alert.alert("Please allow gallery permission");
      }

    })();

  }, []);

  // ================= PICK VIDEO =================

  const pickVideo = async () => {

    try {

      const res = await ImagePicker.launchImageLibraryAsync({

        mediaTypes: ImagePicker.MediaTypeOptions.Videos,

        allowsEditing: false,

        quality: 0.3, // VERY IMPORTANT (reduce Render crash)

      });

      if (!res.canceled) {

        const selected = res.assets[0];

        console.log("Selected:", selected);

        setFile(selected);

        Alert.alert("Video selected");

      }

    } catch (error) {

      console.log(error);

      Alert.alert("Video selection failed");

    }

  };

  // ================= UPLOAD VIDEO =================

  const uploadVideo = async () => {

    if (!file) {

      Alert.alert("Select video first");

      return;

    }

    try {

      setLoading(true);

      setResult("Uploading and analyzing...");

      const formData = new FormData();

      formData.append("file", {

        uri:
          Platform.OS === "android"
            ? file.uri
            : file.uri.replace("file://", ""),

        name: file.fileName || "video.mp4",

        type: file.mimeType || "video/mp4",

      } as any);

      console.log("Uploading to:", SERVER_URL);

      const response = await axios({

        method: "POST",

        url: SERVER_URL,

        data: formData,

        headers: {
          "Content-Type": "multipart/form-data",
        },

        timeout: 300000, // 5 min

      });

      console.log("Server response:", response.data);

      if (response.data?.content_summary) {

        setResult(response.data.content_summary);

      } else {

        setResult("Analysis completed but no summary");

      }

    } catch (error: any) {

      console.log("UPLOAD ERROR:", error);

      if (error.response) {

        console.log("Server error:", error.response.data);

        setResult("Server error");

      }

      else if (error.request) {

        setResult("Cannot reach server");

      }

      else {

        setResult("Upload failed");

      }

    }

    finally {

      setLoading(false);

    }

  };

  // ================= UI =================

  return (

    <View style={styles.container}>

      <Text style={styles.title}>
        VideoGPT Mobile
      </Text>

      <Button
        title="Select Video"
        onPress={pickVideo}
      />

      <View style={{ height: 15 }} />

      <Button
        title="Upload and Analyze"
        onPress={uploadVideo}
      />

      <View style={{ height: 20 }} />

      {loading && (
        <ActivityIndicator size="large" />
      )}

      <Text style={styles.result}>
        {result}
      </Text>

    </View>

  );

}

// ================= STYLE =================

const styles = StyleSheet.create({

  container: {

    flex: 1,

    justifyContent: "center",

    alignItems: "center",

    padding: 20,

  },

  title: {

    fontSize: 26,

    fontWeight: "bold",

    marginBottom: 20,

  },

  result: {

    marginTop: 20,

    fontSize: 18,

    textAlign: "center",

  },

});
