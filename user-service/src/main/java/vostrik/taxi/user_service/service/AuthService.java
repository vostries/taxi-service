package vostrik.taxi.user_service.service;

import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import vostrik.taxi.user_service.dto.*;
import vostrik.taxi.user_service.entity.User;
import vostrik.taxi.user_service.exception.BadRequestException;
import vostrik.taxi.user_service.repository.UserRepository;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PassengerService passengerService;
    private final DriverService driverService;
    private final JwtService jwtService;

    private final PasswordEncoder passwordEncoder;

    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new BadRequestException("Email already registered");
        }

        Long userId;
        String userType = request.getUserType().toUpperCase();

        if ("PASSENGER".equals(userType)) {
            PassengerResponse passenger = passengerService.createPassenger(
                    PassengerRequest.builder()
                            .name(request.getName())
                            .email(request.getEmail())
                            .phone(request.getPhone())
                            .build());
            userId = passenger.getId();
        } else if ("DRIVER".equals(userType)) {
            DriverResponse driver = driverService.createDriver(
                    DriverRequest.builder()
                            .name(request.getName())
                            .email(request.getEmail())
                            .phone(request.getPhone())
                            .licenseNumber(request.getLicenseNumber())
                            .build());
            userId = driver.getId();
        } else {
            throw new BadRequestException("Invalid user type: " + userType);
        }

        User user = User.builder()
                .email(request.getEmail())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .userType(userType)
                .userId(userId)
                .build();
        userRepository.save(user);

        String token = jwtService.generateToken(user.getEmail(), userType, userId);
        return AuthResponse.builder()
                .token(token)
                .userType(userType)
                .userId(userId)
                .build();
    }

    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new BadRequestException("Invalid email or password"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new BadRequestException("Invalid email or password");
        }

        String token = jwtService.generateToken(user.getEmail(), user.getUserType(), user.getUserId());
        return AuthResponse.builder()
                .token(token)
                .userType(user.getUserType())
                .userId(user.getUserId())
                .build();
    }
}
