package vostrik.taxi.trip_service.dto;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DriverResponse {
    private Long id;
    private String name;
    private String email;
    private String phone;
    private String licenseNumber;
    private String status;
}
