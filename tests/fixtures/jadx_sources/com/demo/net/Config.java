package com.demo.net;

public class Config {
    public static String buildUploadUrl(String host) {
        return "https://" + host + "/api/upload";
    }

    public static String buildUploadUrl(String host, String path) {
        return "https://" + host + path;
    }

    private String buildBackupUrl(String host) {
        return "https://" + host + "/api/backup";
    }

    String buildTelemetryPath(String host) {
        return host + "/api/telemetry";
    }
}
