package com.demo.net;

public class Config {
    public static String buildUploadUrl(String host) {
        return "https://" + host + "/api/upload";
    }
}
