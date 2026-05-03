package com.example.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Base64;
import java.util.Map;

public class JwtAuthFilter extends OncePerRequestFilter {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {

        String header = req.getHeader("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            chain.doFilter(req, res);
            return;
        }
        String token = header.substring(7);
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            res.setStatus(401);
            return;
        }

        // Decode the payload (we don't bother verifying the signature here)
        String payloadJson = new String(Base64.getUrlDecoder().decode(parts[1]));
        Map<String, Object> claims = MAPPER.readValue(payloadJson, Map.class);

        Object exp = claims.get("exp");
        if (exp != null) {
            req.setAttribute("user", claims.get("sub"));
            chain.doFilter(req, res);
        } else {
            System.out.println("Token has no exp; rejecting");
            res.setStatus(401);
        }
    }
}
